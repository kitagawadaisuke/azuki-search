#!/usr/bin/env python3
"""
Eテレ番組メタデータ自動収集スクリプト
情報源: tokyofukubukuro.com「おかあさんといっしょ UNOFFICIAL FANCLUB 週報」
       （WordPress REST API経由で取得）

使い方:
    python3 scraper.py             # 直近2週間分
    python3 scraper.py --weeks 4   # 4週間分

出力:
    data.json  ... プロトタイプアプリが読み込むメタデータ
"""

import json
import re
import sys
import time
import argparse
import html as htmllib
from datetime import date, timedelta, datetime
from typing import Optional, List, Dict

import requests
from bs4 import BeautifulSoup

API_BASE = "https://tokyofukubukuro.com/okasan-fc/wp-json/wp/v2/posts"
WEEKLY_CATEGORY_ID = 388  # おかあさんといっしょ週報

UA = "Mozilla/5.0 (EtereSagasukunBot/0.1 personal use)"

SHOWS = {
    "okaasan": {"name": "おかあさんといっしょ", "airtime": "08:00"},
    "inai":    {"name": "いないいないばあっ!",   "airtime": "08:25"},
}


def fetch_weekly_posts(per_page: int = 4) -> List[Dict]:
    """週報カテゴリの最新N件を取得"""
    r = requests.get(
        API_BASE,
        params={"categories": WEEKLY_CATEGORY_ID, "per_page": per_page, "_fields": "id,date,title,content,link"},
        headers={"User-Agent": UA},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def parse_post(post: Dict, item_id_seed: int) -> List[Dict]:
    """
    1記事（1週分）のcontent.renderedをパースして、
    日別の曲・コーナー情報をフラットなリストとして返す。

    HTML構造（実測）:
      <h2 class='date-h2-1line'>2026年4月13日(月)</h2>
      <div class='week_cate'>歌のコーナー > スタジオ (広場)</div>
      <div class='week_tt'><span>1</span> ダンゴムシコロコロ</div>
      <div class='week_castaff'>詞・曲：xxx</div>
      <hr class='week_kugiri'>
      ...
    """
    raw_html = post["content"]["rendered"]
    soup = BeautifulSoup(raw_html, "html.parser")

    items: List[Dict] = []
    item_id = item_id_seed

    DATE_RE = re.compile(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日\s*[\(（]\s*([月火水木金土日])")
    NUM_PREFIX_RE = re.compile(r"^\s*\d+\s*")

    current_date: Optional[date] = None
    current_cate: str = "うた"

    for el in soup.find_all(["h2", "div"]):
        cls = " ".join(el.get("class") or [])

        # 日付見出し
        if el.name == "h2" and "date-h2" in cls:
            text = el.get_text(" ", strip=True)
            m = DATE_RE.search(text)
            if m:
                y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
                try:
                    current_date = date(y, mo, d)
                except ValueError:
                    current_date = None
            continue

        # カテゴリ表示（このすぐあとの week_tt がそのカテゴリに属する）
        if el.name == "div" and "week_cate" in cls:
            cate_text = el.get_text(" > ", strip=True).replace(" > > ", " > ")
            current_cate = classify_cate(cate_text)
            continue

        # 曲名・コーナー名本体
        if el.name == "div" and "week_tt" in cls and current_date is not None:
            t = el.get_text(" ", strip=True)
            t = NUM_PREFIX_RE.sub("", t).strip()
            t = clean_title(t)
            if not t:
                continue
            items.append(make_item(item_id, "okaasan", t, current_cate, current_date))
            item_id += 1

            # 直後の week_castaff にネスト曲（コーナー内で実際に歌われた曲）が
            # 「曲名」or『曲名』形式で書かれてることがある（例: ファンターネ！とうたおう内で「いつもありがとう」）
            sib = el.find_next_sibling("div")
            if sib and "week_castaff" in " ".join(sib.get("class") or []):
                castaff_text = sib.get_text(" ", strip=True)
                m_nested = re.match(r"^\s*[「『]([^」』]+)[」』]", castaff_text)
                if m_nested:
                    nested_title = clean_title(m_nested.group(1))
                    if nested_title and nested_title != t:
                        nested = make_item(item_id, "okaasan", nested_title, "うた", current_date)
                        nested["parent"] = t  # どのコーナー内で歌われたか保持
                        items.append(nested)
                        item_id += 1

    return items


def classify_cate(cate_text: str) -> str:
    """`週_cate`のテキストを大分類にマップ"""
    t = cate_text.replace(" ", "").lower()
    if "人形" in t:
        return "人形劇"
    if "アニメ" in t:
        return "アニメ"
    if "体操" in t or "ダンス" in t or "リズム" in t or "からだ" in t:
        return "体操"
    if "歌" in t or "うた" in t or "ソング" in t:
        return "うた"
    if "兄姉" in t:
        return "うた"
    return "コーナー"


def clean_title(s: str) -> str:
    s = s.strip().strip("「」『』〈〉【】[]()（）　 ")
    if len(s) < 1 or len(s) > 50:
        return ""
    return s


def make_item(item_id: int, show_key: str, title: str, section: str, d: date) -> Dict:
    return {
        "id": item_id,
        "show": show_key,
        "title": title,
        "corner": section,
        "date": d.isoformat(),
        "airtime": SHOWS[show_key]["airtime"],
        "offset": "",
        "order": 0,  # 後で日付ごとに振り直す
        "fav": False,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weeks", type=int, default=2, help="何週間分取るか（デフォルト2）")
    ap.add_argument("--out", default="data.json")
    args = ap.parse_args()

    print(f"📡 fetching latest {args.weeks} weekly reports from tokyofukubukuro.com ...")
    posts = fetch_weekly_posts(per_page=max(args.weeks, 2))
    print(f"  → {len(posts)} 記事取得")

    all_items: List[Dict] = []
    seed = 10000
    for p in posts:
        title = htmllib.unescape(p["title"]["rendered"])
        items = parse_post(p, seed)
        print(f"  - {p['date'][:10]} 「{title}」 → {len(items)}件抽出")
        all_items.extend(items)
        seed += 1000

    # 直近 args.weeks*7 日でフィルタ
    cutoff = date.today() - timedelta(days=args.weeks * 7)
    all_items = [x for x in all_items if date.fromisoformat(x["date"]) >= cutoff]

    # 重複除去（同日・同曲）
    seen = set()
    deduped = []
    for x in all_items:
        key = (x["date"], x["show"], x["title"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(x)

    # 日付＋番組ごとに放送順序（order）を振る
    by_day: Dict[tuple, int] = {}
    for x in deduped:
        k = (x["date"], x["show"])
        by_day[k] = by_day.get(k, 0) + 1
        x["order"] = by_day[k]

    print(f"\n✅ 合計 {len(deduped)} 件、{args.out} に保存（重複除去後）")
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "source": "tokyofukubukuro.com okasan-fc weekly report (WP REST API)",
            "items": deduped,
        }, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
