#!/usr/bin/env python3
"""
Claude API で曲・コーナーのメタデータを自動生成して keywords.json を充実させる。

使い方:
    export ANTHROPIC_API_KEY=sk-ant-...
    python3 enrich.py               # 不足分を全て埋める
    python3 enrich.py --limit 20    # 上限を指定
    python3 enrich.py --dry-run     # APIを叩かずに候補のみ列挙

出力:
    keywords.json を上書き（既存エントリは温存、新規エントリのみ追加）

コスト目安:
    Claude Haiku 4.5 で100曲 ≒ $0.05〜$0.10
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

HERE = Path(__file__).parent

PROMPT = """\
NHK Eテレ「おかあさんといっしょ」「いないいないばあっ!」で放送される曲・コーナーのメタデータを生成します。
以下の曲（またはコーナー）について、検索性を最大化するための情報を JSON で返してください。

曲名/コーナー名: 「{title}」
分類: {corner}

指示:
- keywords: 親が「ねえあれ見たい！」と言った時に思い出しそうな検索語を 5〜12個
  - 歌詞の印象的な単語（「太鼓」「ドンドン」「ピカピカ」など）
  - 擬音・擬態語
  - 登場キャラ・題材（動物・乗り物・食べ物・自然）
  - ムード（元気・切ない・おどけた 等）
  - 別名・通称・季節
  - ひらがな・カタカナ・漢字のバリエーションも含めて
- mood: 「元気」「優しい」「切ない」「楽しい」「感動」「ユーモア」「にぎやか」「なつかしい」のどれか一つ
- snippets: 歌詞の印象的なフレーズを 1〜3 個（配列）
  - 各 5〜15文字程度の短いフレーズ
  - 「歌い出し」「サビ」「印象的な擬音部分」など
  - 著作権配慮で短いものに留める（一節以内）
  - わからない曲は []
- snippet: snippets の最初のフレーズ（後方互換用、なければ空文字）
- theme: 歌の内容・テーマを30〜60文字で一文要約（描写であって歌詞ではない）
  - 例：「大小の太鼓を擬音で叩いて鳴らす元気な童謡」
  - 例：「動物たちが森でかくれんぼする可愛い情景の歌」
  - 著作権セーフ、知らない曲は空文字

知らない曲の場合は推測せず、keywords を短めに、snippets を [] で。
厳密に下記のJSONのみ返してください（コードブロック・解説文なし）：

{{"keywords": ["...", "..."], "mood": "...", "snippets": ["...", "..."], "snippet": "...", "theme": "..."}}
"""


def load_keywords() -> Dict:
    p = HERE / "keywords.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def save_keywords(data: Dict):
    p = HERE / "keywords.json"
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_data_titles() -> List[tuple]:
    """data.json から (title, corner) のユニークセット"""
    p = HERE / "data.json"
    if not p.exists():
        print("⚠ data.json がまだない。先に scraper.py を実行してくれ", file=sys.stderr)
        sys.exit(1)
    d = json.loads(p.read_text(encoding="utf-8"))
    seen = {}
    for x in d["items"]:
        key = x["title"]
        if key not in seen:
            seen[key] = x.get("corner", "うた")
    return list(seen.items())


def call_claude(title: str, corner: str, client) -> Optional[Dict]:
    try:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            messages=[{"role": "user", "content": PROMPT.format(title=title, corner=corner)}],
        )
        text = msg.content[0].text.strip()
        if "```" in text:
            text = text.split("```")[1].lstrip("json").strip()
        parsed = json.loads(text)
        if not isinstance(parsed.get("keywords"), list):
            return None
        snippets = parsed.get("snippets") or []
        if not isinstance(snippets, list):
            snippets = []
        snippets = [s for s in snippets if isinstance(s, str) and s.strip()][:3]
        snippet = parsed.get("snippet") or (snippets[0] if snippets else "")
        return {
            "keywords": [k for k in parsed["keywords"] if isinstance(k, str)][:15],
            "mood": parsed.get("mood", "") or "",
            "snippet": snippet,
            "snippets": snippets,
            "theme": parsed.get("theme", "") or "",
        }
    except Exception as e:
        print(f"  ⚠ Claude失敗 [{title}]: {e}", file=sys.stderr)
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="最大件数（0=無制限）")
    ap.add_argument("--dry-run", action="store_true", help="API呼ばず候補列挙だけ")
    ap.add_argument("--overwrite", action="store_true", help="既存エントリも再生成")
    args = ap.parse_args()

    titles = load_data_titles()
    existing = load_keywords()
    skip_meta_keys = {"_comment", "_format"}

    # 処理対象: data.jsonに存在するが keywords.json に未充填 or 新フィールド未付与のもの
    # 「充填済み」の条件: keywords あり AND snippets/theme どちらかあり（新スキーマ）
    targets = []
    for title, corner in titles:
        if title in skip_meta_keys:
            continue
        ent = existing.get(title) if isinstance(existing.get(title), dict) else None
        has_kw = ent and ent.get("keywords")
        has_new_fields = ent and (ent.get("snippets") or ent.get("theme"))
        fully_done = has_kw and has_new_fields
        if fully_done and not args.overwrite:
            continue
        targets.append((title, corner))

    print(f"📊 data.json 内ユニーク数: {len(titles)}")
    print(f"📊 既にエントリあり: {sum(1 for t,_ in titles if isinstance(existing.get(t), dict) and existing[t].get('keywords'))}")
    print(f"📊 今回エンリッチ対象: {len(targets)}")
    if args.limit:
        targets = targets[:args.limit]
        print(f"📊 --limit により {len(targets)} 件に制限")

    if args.dry_run:
        for t, c in targets:
            print(f"  - [{c}] {t}")
        return

    if not targets:
        print("✅ 追加対象なし")
        return

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY が未設定。export してから実行してくれ")
        print("   キー取得 → https://console.anthropic.com/settings/keys")
        sys.exit(1)
    try:
        import anthropic
    except ImportError:
        print("❌ anthropic SDK 未インストール: pip install --user anthropic")
        sys.exit(1)
    client = anthropic.Anthropic(api_key=api_key)

    added = 0
    for i, (title, corner) in enumerate(targets, 1):
        print(f"  [{i}/{len(targets)}] {title} ... ", end="", flush=True)
        result = call_claude(title, corner, client)
        if result:
            existing[title] = result
            added += 1
            print(f"kw={len(result['keywords'])} mood={result['mood']}")
            # 途中経過を保存（途中で止まっても成果物を残す）
            if added % 10 == 0:
                save_keywords(existing)
        else:
            print("スキップ")
        time.sleep(0.3)  # 礼儀（レート対策）

    save_keywords(existing)
    print(f"\n💾 keywords.json 更新: +{added} 件")


if __name__ == "__main__":
    main()
