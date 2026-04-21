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
from pathlib import Path
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
    current_cate_full: str = "うた"

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
            current_cate_full = re.sub(r"\s+", " ", cate_text)
            current_cate = classify_cate(cate_text)
            continue

        # 曲名・コーナー名本体
        if el.name == "div" and "week_tt" in cls and current_date is not None:
            t = el.get_text(" ", strip=True)
            t = NUM_PREFIX_RE.sub("", t).strip()
            t = clean_title(t)
            if not t:
                continue
            new_item = make_item(item_id, "okaasan", t, current_cate, current_date)
            # 細分類（week_cate のフルパス）も保存
            new_item["subcategory"] = current_cate_full
            items.append(new_item)
            item_id += 1

            # 直後の week_castaff から credits 情報（作詞・曲・出演）を解析
            sib = el.find_next_sibling("div")
            if sib and "week_castaff" in " ".join(sib.get("class") or []):
                castaff_text = sib.get_text("\n", strip=True)
                credits = parse_credits(castaff_text)
                if credits:
                    new_item["credits"] = credits

                # ネスト曲（コーナー内で実際に歌われた曲）
                m_nested = re.match(r"^\s*[「『]([^」』]+)[」』]", castaff_text)
                if m_nested:
                    nested_title = clean_title(m_nested.group(1))
                    if nested_title and nested_title != t:
                        nested = make_item(item_id, "okaasan", nested_title, "うた", current_date)
                        nested["parent"] = t
                        nested["subcategory"] = current_cate_full
                        # ネスト曲のクレジットは castaff 全体から推定
                        nested_credits = parse_credits(castaff_text)
                        if nested_credits:
                            nested["credits"] = nested_credits
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


def parse_credits(castaff_text: str) -> Optional[Dict]:
    """
    week_castaff の改行区切りテキストから credits を抽出する。
    例:
      詞：小林純一／曲：中田喜直／編曲：森悠也
      出演：花田ゆういちろう、ながたまや、佐久本和夢、アンジェ
      歌唱：花田ゆういちろう、ながたまや
      原作：有賀忍／脚本：鈴木信博／音楽：渋谷毅
      アニメーション：キノボリー
    戻り値: {
      "lyrics": ["小林純一"],
      "music":  ["中田喜直"],
      "arrange":["森悠也"],
      "cast":   ["花田ゆういちろう", "ながたまや", "佐久本和夢", "アンジェ"],
      "vocals": ["花田ゆういちろう", "ながたまや"],
      "anim":   ["キノボリー"],
      "original": ["有賀忍"],
      "script": ["鈴木信博"],
      "other":  ["音楽：渋谷毅"]
    }
    """
    if not castaff_text:
        return None
    out: Dict[str, List[str]] = {}
    field_map = {
        "詞": "lyrics", "作詞": "lyrics",
        "曲": "music", "作曲": "music",
        "編曲": "arrange",
        "歌": "vocals", "歌唱": "vocals",
        "出演": "cast",
        "原作": "original",
        "脚本": "script",
        "演出": "director",
        "監督": "director",
        "アニメーション": "anim", "イラスト": "anim",
        "振付": "choreo", "振付け": "choreo",
        "音楽": "bgm",
    }
    # 改行・／・/ で分割された各フラグメントを処理
    fragments = re.split(r"[\n／/]", castaff_text)
    for frag in fragments:
        frag = frag.strip().strip("「」『』")
        if not frag:
            continue
        # 「キー：値」形式
        m = re.match(r"^\s*([\u4e00-\u9faf]+)\s*[:：]\s*(.+)$", frag)
        if not m:
            continue
        key_jp = m.group(1)
        val = m.group(2).strip()
        # 値の中の「、」「,」で複数人分割
        persons = [p.strip() for p in re.split(r"[、,]", val) if p.strip()]
        field = field_map.get(key_jp, "other")
        out.setdefault(field, []).extend(persons)
    # 空なら None
    return out if out else None


_KEYWORDS_DB: Optional[Dict] = None

def load_keywords_db() -> Dict:
    global _KEYWORDS_DB
    if _KEYWORDS_DB is None:
        path = Path(__file__).parent / "keywords.json"
        if path.exists():
            _KEYWORDS_DB = json.loads(path.read_text(encoding="utf-8"))
        else:
            _KEYWORDS_DB = {}
    return _KEYWORDS_DB


def make_item(item_id: int, show_key: str, title: str, section: str, d: date) -> Dict:
    kw_db = load_keywords_db()
    entry = kw_db.get(title, {}) if isinstance(kw_db.get(title), dict) else {}
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
        "keywords": entry.get("keywords", []),
        "mood": entry.get("mood", ""),
        "snippet": entry.get("snippet", ""),
    }


def generate_inai_baa_items(weeks: int, start_id: int) -> List[Dict]:
    """
    いないいないばあっ！の予測データ生成。
    実際の週報ソースが存在しないため、公式把握範囲のテンプレートから
    平日（月〜金）分の推定放送内容を生成する。
    OP/ED/月歌は共通、他曲はローテーション。
    """
    tmpl_path = Path(__file__).parent / "inai_baa_template.json"
    if not tmpl_path.exists():
        return []
    tmpl = json.loads(tmpl_path.read_text(encoding="utf-8"))

    common = tmpl.get("common_items", [])
    rotating_songs = tmpl.get("rotating_songs", [])
    rotating_anime = tmpl.get("rotating_anime", [])

    items: List[Dict] = []
    item_id = start_id
    today = date.today()
    # 直近 weeks*7 日分、平日のみ（いないばあは月〜金放送）
    for delta in range(weeks * 7):
        d = today - timedelta(days=delta)
        if d.weekday() >= 5:  # 土日スキップ
            continue

        # OP（order=1）
        for c in common:
            if c.get("subcategory", "").startswith("OP"):
                items.append(make_inai_item(item_id, c, d, c["order"], tag="predicted"))
                item_id += 1

        # 曜日ローテの歌 2〜3曲（曜日で循環）
        idx = (d.weekday()) % len(rotating_songs)
        for offset in range(3):
            song = rotating_songs[(idx + offset) % len(rotating_songs)]
            items.append(make_inai_item(item_id, song, d, 2 + offset, tag="predicted"))
            item_id += 1

        # アニメ（曜日で決める）
        anime = rotating_anime[d.weekday() % len(rotating_anime)]
        items.append(make_inai_item(item_id, anime, d, 5, tag="predicted"))
        item_id += 1

        # 月歌・ED（後ろ）
        for c in common:
            sc = c.get("subcategory", "")
            if sc.startswith("2025") or sc.startswith("ED"):
                items.append(make_inai_item(item_id, c, d, c["order"], tag="predicted"))
                item_id += 1

    return items


def make_inai_item(item_id: int, tmpl: Dict, d: date, order: int, tag: str = "") -> Dict:
    return {
        "id": item_id,
        "show": "inai",
        "title": tmpl["title"],
        "corner": tmpl.get("corner", "うた"),
        "date": d.isoformat(),
        "airtime": SHOWS["inai"]["airtime"],
        "offset": "",
        "order": order,
        "fav": False,
        "keywords": tmpl.get("keywords", []),
        "mood": tmpl.get("mood", ""),
        "snippet": tmpl.get("snippet", ""),
        "subcategory": tmpl.get("subcategory", ""),
        "source_tag": tag,  # "predicted" = 予測、実データではない
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weeks", type=int, default=4, help="何週間分取るか（デフォルト4）")
    ap.add_argument("--out", default="data.json")
    ap.add_argument("--no-inai", action="store_true", help="いないいないばあの予測データを含めない")
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

    # 直近 args.weeks*7 日でフィルタ（今日を含む）
    cutoff = date.today() - timedelta(days=args.weeks * 7 - 1)
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

    # いないいないばあ予測データを追加
    if not args.no_inai:
        next_id = max((x["id"] for x in deduped), default=0) + 1
        inai_items = generate_inai_baa_items(args.weeks, next_id)
        # 重複除去（同日・同曲）
        inai_seen = set()
        for x in inai_items:
            key = (x["date"], x["show"], x["title"])
            if key in inai_seen:
                continue
            inai_seen.add(key)
            deduped.append(x)
        print(f"🔮 いないいないばあ予測データ: {len(inai_items)}件追加")

    print(f"\n✅ 合計 {len(deduped)} 件、{args.out} に保存（重複除去後）")
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "source": "tokyofukubukuro.com okasan-fc weekly report (WP REST API)",
            "items": deduped,
        }, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
