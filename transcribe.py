#!/usr/bin/env python3
"""
Eテレ番組メタデータ抽出パイプライン

   [録画音声 .ts/.m4a/.wav]
        ↓ (ffmpeg)
   [16kHz mono wav]
        ↓ (whisper.cpp ローカル or OpenAI Whisper API)
   [文字起こし（タイムスタンプ付き）]
        ↓ (Claude API)
   [曲・コーナー構造化JSON]
        ↓ (merge)
   [data.json に追記]

使い方:
    # フルパイプライン
    python3 transcribe.py recording.ts --show okaasan --date 2026-04-20

    # 動作検証（音声なし、テキストだけ）
    python3 transcribe.py --text-input sample_transcript.txt --show okaasan --date 2026-04-20

    # Whisper段だけ
    python3 transcribe.py recording.ts --whisper-only

    # 抽出段だけ（既存の文字起こしJSON）
    python3 transcribe.py --segments-input transcript.json --show okaasan --date 2026-04-20

環境変数:
    ANTHROPIC_API_KEY  ... Claude API（曲名抽出に必要）
    OPENAI_API_KEY     ... OpenAI Whisper API（whisper-cppがない場合のフォールバック）

依存:
    pip install --user anthropic openai
    brew install ffmpeg whisper-cpp   # Mac: ローカルWhisper（推奨）
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional


SHOWS = {
    "okaasan": {"name": "おかあさんといっしょ", "airtime": "08:00"},
    "inai":    {"name": "いないいないばあっ!",   "airtime": "08:25"},
}

EXTRACT_PROMPT = """\
あなたはNHK Eテレ「{show_name}」の放送内容を解析する専門家です。
以下は録画音声の文字起こし（Whisperの出力。タイムスタンプ付き、誤認識あり）です。
この放送に登場した「曲」「コーナー」「人形劇」「アニメ」「体操」などのセグメントを、
放送順に正確に抽出してJSON配列で返してください。

ルール:
1. 曲タイトルは公式表記に正規化（例：「ぱぴぷぺぽ」「からだ☆ダンダン」「きんらきら ぽん」）
2. コーナー名は番組内で呼ばれている名称（「ガラピコぷ〜」「ファンターネ！」「オタマジックショー」等）
3. 並び順は放送順そのまま
4. 各エントリーに type を付与: "うた" / "人形劇" / "アニメ" / "体操" / "コーナー"
5. 確信度の低い曲名は title に推測値、推測フラグ guess: true を付ける
6. 文字起こしのノイズ（観客拍手・効果音・誤認識）は除外

出力JSON形式（厳密に従うこと、解説文は付けない）:
{{
  "items": [
    {{"order": 1, "type": "うた", "title": "ぱぴぷぺぽ", "guess": false}},
    {{"order": 2, "type": "コーナー", "title": "シルエットはかせ", "guess": false}}
  ]
}}

文字起こし:
{transcript}
"""


# =============== 1. 音声 → wav 正規化 ===============

def to_wav(input_path: str, out_dir: Path) -> Path:
    """ffmpegで16kHz mono WAVに変換（Whisper入力に最適）"""
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg がインストールされていません。`brew install ffmpeg`")
    out = out_dir / "audio.wav"
    print(f"  🎵 ffmpeg → {out}")
    subprocess.run([
        "ffmpeg", "-y", "-i", input_path,
        "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
        str(out)
    ], check=True, capture_output=True)
    return out


# =============== 2. 文字起こし ===============

def transcribe_local(wav_path: Path) -> List[Dict]:
    """whisper-cpp（ローカル・高速）で文字起こし"""
    if not shutil.which("whisper-cpp"):
        return []
    print("  🗣  whisper-cpp（ローカル）...")
    result = subprocess.run([
        "whisper-cpp", "-m", os.path.expanduser("~/whisper-models/ggml-medium.bin"),
        "-l", "ja", "-oj", "-of", str(wav_path.with_suffix("")), str(wav_path)
    ], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ⚠ whisper-cpp失敗: {result.stderr[:200]}", file=sys.stderr)
        return []
    json_path = wav_path.with_suffix(".json")
    if not json_path.exists():
        return []
    data = json.loads(json_path.read_text())
    return [
        {"start": s["offsets"]["from"]/1000, "end": s["offsets"]["to"]/1000, "text": s["text"]}
        for s in data.get("transcription", [])
    ]


def transcribe_openai(wav_path: Path) -> List[Dict]:
    """OpenAI Whisper APIで文字起こし（whisper-cppがない場合のフォールバック）"""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY が未設定")
    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError("openai SDK 未インストール: `pip install --user openai`")
    print("  🗣  OpenAI Whisper API ...")
    client = OpenAI(api_key=api_key)
    with open(wav_path, "rb") as f:
        resp = client.audio.transcriptions.create(
            model="whisper-1", file=f, language="ja",
            response_format="verbose_json", timestamp_granularities=["segment"]
        )
    return [
        {"start": s["start"], "end": s["end"], "text": s["text"]}
        for s in resp.segments
    ]


def transcribe(wav_path: Path) -> List[Dict]:
    segs = transcribe_local(wav_path)
    if segs:
        return segs
    return transcribe_openai(wav_path)


# =============== 3. Claude で構造化 ===============

def segments_to_text(segments: List[Dict]) -> str:
    """[start - end] text 形式の単純なテキストに変換"""
    lines = []
    for s in segments:
        ts = f"[{int(s['start']//60):02}:{int(s['start']%60):02} - {int(s['end']//60):02}:{int(s['end']%60):02}]"
        lines.append(f"{ts} {s['text'].strip()}")
    return "\n".join(lines)


def extract_with_claude(transcript: str, show_key: str) -> List[Dict]:
    """Claude API で曲・コーナーを構造化抽出"""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY が未設定")
    try:
        import anthropic
    except ImportError:
        raise RuntimeError("anthropic SDK 未インストール: `pip install --user anthropic`")

    print("  🤖 Claude API（曲名・コーナー抽出）...")
    client = anthropic.Anthropic(api_key=api_key)
    prompt = EXTRACT_PROMPT.format(
        show_name=SHOWS[show_key]["name"],
        transcript=transcript[:30000],  # 上限ガード
    )
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",  # 安・速
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text.strip()
    # JSON部分を抽出（コードブロック対応）
    if "```" in text:
        text = text.split("```")[1].lstrip("json").strip()
    return json.loads(text).get("items", [])


# =============== 4. data.json マージ ===============

def merge_into_data(items: List[Dict], show_key: str, broadcast_date: date,
                    data_path: str = "data.json") -> int:
    """既存 data.json に追記。同じ (date, show, title) は重複扱いでスキップ"""
    if Path(data_path).exists():
        existing = json.load(open(data_path))
    else:
        existing = {"items": [], "source": "transcribe"}

    seen = {(x["date"], x["show"], x["title"]) for x in existing["items"]}
    next_id = max((x["id"] for x in existing["items"]), default=0) + 1
    added = 0
    for it in items:
        title = it["title"].strip()
        if not title:
            continue
        key = (broadcast_date.isoformat(), show_key, title)
        if key in seen:
            continue
        seen.add(key)
        existing["items"].append({
            "id": next_id,
            "show": show_key,
            "title": title,
            "corner": it.get("type", "コーナー"),
            "date": broadcast_date.isoformat(),
            "airtime": SHOWS[show_key]["airtime"],
            "offset": "",
            "order": it.get("order", 999),
            "fav": False,
            "source": "transcribe",
            "guess": it.get("guess", False),
        })
        next_id += 1
        added += 1

    existing["generated_at"] = datetime.now().isoformat(timespec="seconds")
    json.dump(existing, open(data_path, "w"), ensure_ascii=False, indent=2)
    return added


# =============== CLI ===============

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("audio", nargs="?", help="録画ファイル（.ts/.m4a/.wav等）")
    ap.add_argument("--text-input", help="文字起こし済みテキスト（動作検証用）")
    ap.add_argument("--segments-input", help="既存のセグメントJSON")
    ap.add_argument("--show", choices=list(SHOWS.keys()), default="okaasan")
    ap.add_argument("--date", default=date.today().isoformat(), help="放送日 YYYY-MM-DD")
    ap.add_argument("--whisper-only", action="store_true", help="文字起こしまで")
    ap.add_argument("--data-path", default="data.json")
    args = ap.parse_args()

    broadcast_date = date.fromisoformat(args.date)
    print(f"📺 {SHOWS[args.show]['name']} / {broadcast_date} の処理を開始")

    # 入力ソース判定
    if args.text_input:
        transcript = Path(args.text_input).read_text()
        print(f"  📝 テキスト入力: {len(transcript)} 文字")
    elif args.segments_input:
        segs = json.load(open(args.segments_input))
        transcript = segments_to_text(segs)
        print(f"  📝 セグメント入力: {len(segs)} 件")
    elif args.audio:
        with tempfile.TemporaryDirectory() as tmp:
            wav = to_wav(args.audio, Path(tmp))
            segs = transcribe(wav)
            print(f"  ✅ {len(segs)} セグメント取得")
            if args.whisper_only:
                print(json.dumps(segs, ensure_ascii=False, indent=2))
                return
            transcript = segments_to_text(segs)
    else:
        ap.error("音声ファイル、--text-input、--segments-input のいずれかが必要")

    # Claude で構造化
    items = extract_with_claude(transcript, args.show)
    print(f"  ✅ {len(items)} 件の曲/コーナーを抽出")
    for it in items[:5]:
        flag = " (推測)" if it.get("guess") else ""
        print(f"     {it.get('order','?'):>2}. [{it.get('type','?'):4}] {it['title']}{flag}")
    if len(items) > 5:
        print(f"     ... 他 {len(items)-5} 件")

    # マージ
    added = merge_into_data(items, args.show, broadcast_date, args.data_path)
    print(f"\n💾 {args.data_path} に {added} 件追加（重複除外後）")


if __name__ == "__main__":
    main()
