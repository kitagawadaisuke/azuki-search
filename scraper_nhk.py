#!/usr/bin/env python3
"""
NHK公式 番組ページからの放送内容スクレイパー (おかあさんといっしょ / いないいないばあっ!)

情報源:
  - シリーズページHTML内に約2週間分の broadcastevent ID が埋め込まれている
  - 各放送詳細: https://api.web.nhk/r8/t/broadcastevent/be/{eventId}.json

対応番組:
  - okaasan : おかあさんといっしょ (series-tep-ZPW9W9XN42)  ← 散文description
  - inai    : いないいないばあっ!  (series-tep-E4G3263MG7)  ← ▼区切りdescription

使い方:
    python3 scraper_nhk.py                      # おかあさんといっしょ → nhk_data.json
    python3 scraper_nhk.py --show inai          # いないいないばあ → nhk_data.json
    python3 scraper_nhk.py --show okaasan -v
"""
import argparse
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import requests

# ---------------------------------------------------------------------------
# 番組定義
# ---------------------------------------------------------------------------
SHOWS = {
    "okaasan": {
        "series_id": "ZPW9W9XN42",
        "page_url": "https://www.nhk.jp/p/okaasan/ts/ZPW9W9XN42/",
        "parser": "prose",   # 散文 + 「」抽出
    },
    "inai": {
        "series_id": "E4G3263MG7",
        "page_url": "https://www.nhk.jp/p/inaiinai/ts/E4G3263MG7/",
        "parser": "delimited",  # ▼ 区切り
    },
}

API_BASE = "https://api.web.nhk/r8"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (EtereSagasukunBot/0.3 personal use)",
    "Origin": "https://www.nhk.jp",
    "Referer": "https://www.nhk.jp/",
}

BE_ID_RE = re.compile(r"broadcastevent/be/((?:e1|g1|e3)-[0-9]+-[0-9]+)\.json")
QUOTE_RE = re.compile(r"「([^」]+)」")


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------
def fetch_series_page(show_key: str) -> str:
    cfg = SHOWS[show_key]
    r = requests.get(cfg["page_url"], headers=HEADERS, timeout=15, allow_redirects=True)
    r.raise_for_status()
    return r.text


def extract_event_ids(html: str) -> List[str]:
    return sorted(set(BE_ID_RE.findall(html)))


def fetch_event(event_id: str) -> Dict:
    url = f"{API_BASE}/t/broadcastevent/be/{event_id}.json"
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------------------
# 分類器: おかあさんといっしょ用 (散文文脈ベース)
# ---------------------------------------------------------------------------
def classify_okaasan(title: str, description: str) -> str:
    pat = f"「{title}」"
    idx = description.find(pat)
    if idx < 0:
        return "うた"
    prefix = description[max(0, idx - 50): idx]
    suffix = description[idx + len(pat): idx + len(pat) + 30]

    if suffix.startswith("のリクエスト曲") or suffix.startswith("のコーナー"):
        return "コーナー"
    if re.search(r"親子体操$|体操$|ダンスは$", prefix):
        return "体操"
    if re.search(r"おはなし$|人形劇$", prefix):
        return "人形劇"
    if re.search(r"アニメ$", prefix) and "アニメーション" not in prefix[-15:]:
        return "アニメ"
    if re.search(r"歌うのは(?:[^「]{0,10})?$|月の歌(?:は)?$|今月の歌$", prefix):
        return "うた"
    if re.search(r"リクエスト曲は$", prefix):
        return "うた"
    if re.search(r"コーナー$|チャンネル$", prefix):
        return "コーナー"

    if "ダンダン" in title or "体操" in title:
        return "体操"
    if "チャンネル" in title or "ゆうびん" in title:
        return "コーナー"
    if title in ("ファンターネ！", "こんなこいるかな"):
        return "人形劇"
    return "うた"


# ---------------------------------------------------------------------------
# 分類器: いないいないばあっ!用 (▼区切り + プレフィクス語)
# ---------------------------------------------------------------------------
def classify_inai(prefix_word: str, title: str) -> str:
    p = (prefix_word or "").strip()
    if p in ("童謡", "歌", "うた"):
        return "うた"
    if p in ("アニメ", "アニメーション"):
        return "アニメ"
    if p in ("たいそう", "体操"):
        return "体操"
    if p in ("コーナー",):
        return "コーナー"

    # title内のヒント
    if any(k in title for k in ("たいそう", "体操", "ぐるぐる", "ダンス")):
        return "体操"
    if title in ("ワンワン", "うーたん"):
        return "コーナー"
    return "コーナー"  # inaiは ▼以降は基本コーナー扱い (歌・アニメ・体操が明示的)


# ---------------------------------------------------------------------------
# パーサ
# ---------------------------------------------------------------------------
def parse_items_prose(description: str) -> List[Dict]:
    """おかあさんといっしょ形式: 散文中の「」を順番抽出。"""
    seen = set()
    ordered = []
    for t in QUOTE_RE.findall(description):
        t = t.strip()
        if not t or t in seen:
            continue
        seen.add(t)
        ordered.append(t)

    return [
        {
            "title": t,
            "order_hint": idx,
            "section": classify_okaasan(t, description),
        }
        for idx, t in enumerate(ordered, start=1)
    ]


_INAI_SEG_PREFIX_RE = re.compile(r"^(童謡|歌|うた|アニメ|アニメーション|たいそう|体操|コーナー)?")


def parse_items_delimited(description: str) -> List[Dict]:
    """いないいないばあ形式: ▼ 区切りで各セグメントから title を抽出。

    例: "narrative ▼童謡「ぶんぶんぶん」、▼ボールのたび～電車、
         ▼アニメ「のりものタウン～池」、▼たいそう「ぐるぐるどっか～ん！」など。"
    """
    if "▼" not in description:
        # ▼が無ければ prose 扱いにフォールバック
        return parse_items_prose(description)

    # ▼ブロック後ろの定型文 (「映像」と「音」で構成…) を切る
    desc_trimmed = description
    for terminator in ("など。", "。「映像」"):
        i = desc_trimmed.find(terminator)
        if i >= 0:
            desc_trimmed = desc_trimmed[:i]
            break

    parts = desc_trimmed.split("▼")
    # 先頭 (▼前) は導入narrative なのでスキップ
    segments = [p for p in parts[1:] if p.strip()]

    items: List[Dict] = []
    seen: set = set()
    order = 0
    for seg in segments:
        # 末尾の "、" "。" "など" を削る
        seg_clean = seg.strip()
        seg_clean = re.sub(r"(、|。|など。?)$", "", seg_clean).strip()
        if not seg_clean:
            continue

        # プレフィクス語抽出 (この▼ブロック内の全titleにかかる)
        m_pref = _INAI_SEG_PREFIX_RE.match(seg_clean)
        prefix_word = m_pref.group(1) if m_pref else ""
        rest = seg_clean[len(prefix_word):] if prefix_word else seg_clean

        # 同一▼内の全「TITLE」を抽出 (例: ▼うた「A」、「B」、「C」)
        quoted_titles = QUOTE_RE.findall(rest)

        if quoted_titles:
            for title in quoted_titles:
                title = title.strip()
                if not title or title in seen:
                    continue
                seen.add(title)
                order += 1
                items.append({
                    "title": title,
                    "order_hint": order,
                    "section": classify_inai(prefix_word, title),
                })
        else:
            # クォート無し → 先頭フレーズをtitle扱い (コーナー名)
            title = re.split(r"[、。]", rest)[0].strip()
            if not (1 <= len(title) <= 40) or title in seen:
                continue
            seen.add(title)
            order += 1
            items.append({
                "title": title,
                "order_hint": order,
                "section": classify_inai(prefix_word, title),
            })

    return items


# ---------------------------------------------------------------------------
# 1放送イベントのパース
# ---------------------------------------------------------------------------
def parse_event(event: Dict, show_key: str) -> Dict:
    desc = event.get("description") or ""
    if not desc:
        desc = (event.get("detailedDescription") or {}).get("epg200", "")

    ig = event.get("identifierGroup", {}) or {}
    parser = SHOWS[show_key]["parser"]

    if parser == "delimited":
        raw_items = parse_items_delimited(desc)
    else:
        raw_items = parse_items_prose(desc)

    items = [{**ri, "show": show_key, "source": "nhk", "date": ig.get("date", "")}
             for ri in raw_items]

    return {
        "date": ig.get("date", ""),
        "startDate": event.get("startDate", ""),
        "endDate": event.get("endDate", ""),
        "tvEpisodeId": ig.get("tvEpisodeId", ""),
        "broadcastEventId": ig.get("broadcastEventId", ""),
        "episodeName": event.get("name", ""),
        "description": desc,
        "items": items,
    }


# ---------------------------------------------------------------------------
# トップレベルAPI
# ---------------------------------------------------------------------------
def scrape_show(show_key: str, verbose: bool = False) -> Dict:
    if show_key not in SHOWS:
        raise ValueError(f"unknown show: {show_key}")
    cfg = SHOWS[show_key]

    if verbose:
        print(f"📡 fetching {show_key}: {cfg['page_url']}")
    html = fetch_series_page(show_key)
    event_ids = extract_event_ids(html)
    if verbose:
        print(f"  → {len(event_ids)} broadcast events")

    broadcasts: List[Dict] = []
    for eid in event_ids:
        try:
            ev = fetch_event(eid)
            broadcasts.append(parse_event(ev, show_key))
            time.sleep(0.3)
        except Exception as e:
            print(f"  ⚠️  {eid}: {e}")

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source": f"NHK公式 (api.web.nhk/r8 + series-tep-{cfg['series_id']})",
        "show": show_key,
        "series_id": cfg["series_id"],
        "broadcasts": broadcasts,
    }


# 後方互換: 旧名で呼ばれた時 okaasan を返す
def scrape_all() -> Dict:
    return scrape_show("okaasan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", default="okaasan", choices=list(SHOWS.keys()))
    ap.add_argument("--out", default="nhk_data.json")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    data = scrape_show(args.show, verbose=args.verbose)

    if args.verbose:
        for b in data["broadcasts"]:
            print(f"  - {b['date']} 「{b['episodeName']}」 → {len(b['items'])}件")
            for it in b["items"]:
                print(f"      [{it['order_hint']}] {it['section']}: {it['title']}")

    Path(args.out).write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    total = sum(len(b["items"]) for b in data["broadcasts"])
    print(f"✅ {args.show}: {len(data['broadcasts'])} 放送 / 計{total}曲 → {args.out}")


if __name__ == "__main__":
    main()
