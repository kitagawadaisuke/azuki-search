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
    "okaasan": {"name": "おかあさんといっしょ", "airtime": "07:45"},
    "inai":    {"name": "いないいないばあっ!",   "airtime": "08:10"},
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
_CHARACTERS_DB: Optional[List[Dict]] = None

def load_keywords_db() -> Dict:
    global _KEYWORDS_DB
    if _KEYWORDS_DB is None:
        path = Path(__file__).parent / "keywords.json"
        if path.exists():
            _KEYWORDS_DB = json.loads(path.read_text(encoding="utf-8"))
        else:
            _KEYWORDS_DB = {}
    return _KEYWORDS_DB


def load_characters_db() -> List[Dict]:
    global _CHARACTERS_DB
    if _CHARACTERS_DB is None:
        path = Path(__file__).parent / "characters.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            _CHARACTERS_DB = data.get("characters", [])
        else:
            _CHARACTERS_DB = []
    return _CHARACTERS_DB


def detect_characters(item: Dict) -> List[str]:
    """item の title/keywords/credits/parent から登場キャラを検出"""
    chars_db = load_characters_db()
    found = set()
    haystack_parts = [
        item.get("title", ""),
        item.get("parent", "") or "",
        item.get("subcategory", "") or "",
        " ".join(item.get("keywords", [])),
    ]
    if item.get("credits"):
        for v in item["credits"].values():
            haystack_parts.append(" ".join(v))
    haystack = " ".join(haystack_parts)
    for c in chars_db:
        if c.get("show") and c["show"] != item.get("show"):
            continue
        for alias in c.get("aliases", []):
            if alias and alias in haystack:
                found.add(c["key"])
                break
    return sorted(found)


def make_item(item_id: int, show_key: str, title: str, section: str, d: date) -> Dict:
    kw_db = load_keywords_db()
    entry = kw_db.get(title, {}) if isinstance(kw_db.get(title), dict) else {}
    snippets = entry.get("snippets", [])
    snippet = entry.get("snippet", "") or (snippets[0] if snippets else "")
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
        "snippet": snippet,
        "snippets": snippets,
        "theme": entry.get("theme", ""),
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


def normalize_title(s: str) -> str:
    """タイトル比較用の正規化。表記ゆれ吸収のため。"""
    if not s:
        return ""
    # 全角/半角・記号・スペース・伸ばし棒のゆれを吸収
    t = s.strip()
    t = re.sub(r"[ 　\s]+", "", t)
    t = re.sub(r"[!！?？♪☆★・…]", "", t)
    t = t.replace("ヴ", "ブ")
    t = t.replace("ウィ", "イ").replace("ウェ", "エ").replace("ウォ", "オ")
    t = t.replace("ぁ", "あ").replace("ぃ", "い").replace("ぅ", "う").replace("ぇ", "え").replace("ぉ", "お")
    return t.lower()


def merge_nhk_into_items(weekly_items: List[Dict], nhk_data: Dict, next_id: int, show_key: str = "okaasan") -> tuple:
    """既存itemsにNHK公式データをmergeする。

    ルール (Q1=c, Q2=a, Q3=keep):
      - 同日同曲が両方にある場合: 既存の order/credits/keywords を保持、
        title はNHK綴り優先 (差異がある場合のみ更新)、source="nhk+weekly"
      - NHKのみ存在: 仮order(=その日の既存最大order + order_hint)、source="nhk"
      - 既存のみ存在: そのまま (Q3)
      - broadcast_meta[date] = {description, episodeName, tvEpisodeId}

    Args:
      show_key: "okaasan" | "inai" — 対象番組

    Returns: (merged_items, broadcast_meta_by_date)
    """
    # 該当showの既存itemsを (date, normalized_title) で索引
    weekly_index: Dict[tuple, Dict] = {}
    for it in weekly_items:
        if it.get("show") != show_key:
            continue
        weekly_index[(it["date"], normalize_title(it["title"]))] = it

    # その日の最大orderを把握 (NHKのみitemに連番を振るため)
    max_order_by_date: Dict[str, int] = {}
    for it in weekly_items:
        if it.get("show") != show_key:
            continue
        d = it["date"]
        max_order_by_date[d] = max(max_order_by_date.get(d, 0), it.get("order", 0))

    broadcast_meta: Dict[str, Dict] = {}
    nhk_added: List[Dict] = []
    matched_count = 0

    for b in nhk_data.get("broadcasts", []):
        date_str = b.get("date", "")
        if not date_str:
            continue
        # broadcast_metaは1日1放送が基本だが、特番複数あるケースは後勝ち+items統合
        if date_str not in broadcast_meta:
            broadcast_meta[date_str] = {
                "description": b.get("description", ""),
                "episodeName": b.get("episodeName", ""),
                "tvEpisodeId": b.get("tvEpisodeId", ""),
                "broadcastEventId": b.get("broadcastEventId", ""),
                "startDate": b.get("startDate", ""),
                "source": "nhk",
            }
        else:
            # 特番のdescriptionを連結
            existing = broadcast_meta[date_str]
            existing["description"] = (existing["description"] + "\n---\n" + b.get("description", "")).strip()
            existing["episodeName"] = existing["episodeName"] + " / " + b.get("episodeName", "")

        # この放送のorderオフセットは1放送の処理開始時点で固定
        # (broadcast内のorderはhint通りにし、放送間でのみずらす)
        broadcast_base = max_order_by_date.get(date_str, 0)
        broadcast_max = broadcast_base

        for nhk_it in b.get("items", []):
            nhk_title = nhk_it["title"]
            key = (date_str, normalize_title(nhk_title))
            if key in weekly_index:
                wk = weekly_index[key]
                # 週報のorder/credits/keywords保持、titleはNHK綴り優先 (差異時のみ)
                if wk["title"] != nhk_title:
                    wk["title_alt"] = wk["title"]
                    wk["title"] = nhk_title
                wk["source"] = "nhk+weekly"
                matched_count += 1
            else:
                # NHKのみ: 仮order = (放送開始時のbase) + 放送内のorder_hint
                fallback_order = broadcast_base + nhk_it.get("order_hint", 0)
                broadcast_max = max(broadcast_max, fallback_order)
                new_item = {
                    "id": next_id,
                    "show": show_key,
                    "title": nhk_title,
                    "corner": nhk_it.get("section", "うた"),
                    "date": date_str,
                    "airtime": SHOWS[show_key]["airtime"],
                    "offset": "",
                    "order": fallback_order,
                    "fav": False,
                    "keywords": [],
                    "mood": "",
                    "snippet": "",
                    "snippets": [],
                    "theme": "",
                    "subcategory": nhk_it.get("section", "うた"),
                    "source": "nhk",
                }
                # キーワードDBから補強
                kw_db = load_keywords_db()
                entry = kw_db.get(nhk_title, {}) if isinstance(kw_db.get(nhk_title), dict) else {}
                if entry:
                    new_item["keywords"] = entry.get("keywords", [])
                    new_item["mood"] = entry.get("mood", "")
                    snippets = entry.get("snippets", [])
                    new_item["snippets"] = snippets
                    new_item["snippet"] = entry.get("snippet", "") or (snippets[0] if snippets else "")
                    new_item["theme"] = entry.get("theme", "")
                new_item["characters"] = detect_characters(new_item)
                nhk_added.append(new_item)
                next_id += 1

        # この放送が消費したorderレンジを反映 (次の同日放送はその上から振る)
        max_order_by_date[date_str] = broadcast_max

    print(f"  📊 merge: {matched_count} 件マッチ / {len(nhk_added)} 件NHK追加 / {len(broadcast_meta)} 日メタ生成")
    return weekly_items + nhk_added, broadcast_meta


def load_existing(path: str) -> tuple:
    """既存 data.json を読み込む (アーカイブ式 merge 用)"""
    p = Path(path)
    if not p.exists():
        return [], {}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        items = d.get("items", []) or []
        meta = d.get("broadcast_meta", {}) or {}
        # broadcast_meta は番組別ネスト構造に対応
        if isinstance(meta, dict) and "okaasan" not in meta and "inai" not in meta:
            # 旧 flat 構造 → 互換のためそのまま入れとく
            meta = {"okaasan": meta, "inai": {}}
        return items, meta
    except Exception as e:
        print(f"  ⚠️ 既存data.json読み込み失敗: {e}")
        return [], {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weeks", type=int, default=4, help="週報を何週間分取るか（デフォルト4）")
    ap.add_argument("--out", default="data.json")
    ap.add_argument("--no-inai", action="store_true", help="いないいないばあの予測データを含めない")
    ap.add_argument("--no-nhk", action="store_true", help="NHK公式データmergeをスキップ")
    ap.add_argument("--no-archive", action="store_true", help="既存data.jsonを無視して上書き(旧挙動)")
    ap.add_argument("--retain-weeks", type=int, default=4,
                    help="アーカイブ保持期間(週数)。これより古いitemは整理される (default=4)")
    args = ap.parse_args()

    # === Archive式 merge: 既存 data.json を起点として、新規scrape分を追加していく ===
    if args.no_archive:
        existing_items: List[Dict] = []
        archived_meta: Dict[str, Dict] = {"okaasan": {}, "inai": {}}
    else:
        existing_items, archived_meta = load_existing(args.out)
        if existing_items:
            print(f"📦 既存 data.json から {len(existing_items)} 件をアーカイブとしてロード")

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

    # 重複除去（同日・同曲、週報内）
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
        # キャラクター検出
        x["characters"] = detect_characters(x)

    # NHK公式データをmerge (おかあさん + いないいないばあ)
    # broadcast_meta は番組別に保持: {"okaasan": {date: {...}}, "inai": {date: {...}}}
    # ※ 既存アーカイブの broadcast_meta を起点として上書き&追加
    broadcast_meta: Dict[str, Dict] = {
        "okaasan": dict(archived_meta.get("okaasan", {})),
        "inai":    dict(archived_meta.get("inai", {})),
    }
    nhk_inai_dates: set = set()  # NHKでカバー済の日付 → 予測データから除外する
    if not args.no_nhk:
        try:
            import scraper_nhk
            for show_key in ("okaasan", "inai"):
                print(f"📡 fetching NHK official broadcast data: {show_key} ...")
                try:
                    nhk = scraper_nhk.scrape_show(show_key)
                except Exception as e:
                    print(f"  ⚠️  {show_key} NHK fetch失敗: {e}")
                    continue
                print(f"  → {len(nhk['broadcasts'])} 放送取得")
                next_id = max((x["id"] for x in deduped), default=20000) + 1
                if next_id < 20000:
                    next_id = 20000  # NHKのみitem用ID帯
                deduped, meta = merge_nhk_into_items(deduped, nhk, next_id, show_key=show_key)
                # archive: 既存metaに新meta(同日付がある場合上書き)
                broadcast_meta[show_key].update(meta)
                if show_key == "inai":
                    # NHKカバー済日付 = 今回scrapeの日付のみ(過去archive分は除外しない=予測も生成しない)
                    nhk_inai_dates = set(meta.keys())
        except Exception as e:
            print(f"  ⚠️  NHK fetch全体失敗、既存データのみで続行: {e}")

    # いないいないばあ予測データを追加 (NHKでカバーできなかった日付のみ)
    if not args.no_inai:
        next_id = max((x["id"] for x in deduped), default=0) + 1
        inai_items = generate_inai_baa_items(args.weeks, next_id)
        # NHKでカバー済の日付は除外 (公式優先)
        inai_items = [x for x in inai_items if x["date"] not in nhk_inai_dates]
        # 重複除去（同日・同曲）
        inai_seen = set()
        added = 0
        for x in inai_items:
            key = (x["date"], x["show"], x["title"])
            if key in inai_seen:
                continue
            inai_seen.add(key)
            x["characters"] = detect_characters(x)
            deduped.append(x)
            added += 1
        print(f"🔮 いないいないばあ予測データ: {added}件追加 (NHK公式{len(nhk_inai_dates)}日分は除外)")

    # === Archive merge: 既存 items と今回 scrape 結果を統合 ===
    # ルール:
    #   - 同 (date, show, normalized_title) があれば、最新(今回scrape)を優先
    #   - 古い items は touch しない (NHK API から消えた過去日付も保持)
    if existing_items and not args.no_archive:
        new_keys = set()
        for it in deduped:
            new_keys.add((it.get("date"), it.get("show"), normalize_title(it.get("title", ""))))
        # 既存のうち、今回scrapeで上書きされないものは保持
        kept_old = []
        for it in existing_items:
            k = (it.get("date"), it.get("show"), normalize_title(it.get("title", "")))
            if k not in new_keys:
                kept_old.append(it)
        # ID 衝突を避けるため、kept_old のIDを大きな番号にrebase
        if kept_old:
            max_id = max((x.get("id", 0) for x in deduped), default=20000)
            next_id = max(max_id + 1, 30000)
            for it in kept_old:
                # 既存IDがdedupedと重複する場合のみ振り直す
                if any(d.get("id") == it.get("id") for d in deduped):
                    it["id"] = next_id
                    next_id += 1
        deduped = deduped + kept_old
        print(f"📦 archive merge: 新規{len(deduped) - len(kept_old)}件 + 過去保持{len(kept_old)}件 = 合計{len(deduped)}件")

    # === 保持期間 (retention) フィルタ ===
    # 過去 args.retain_weeks 週より古い items は破棄して肥大化を防ぐ
    if args.retain_weeks > 0:
        retain_cutoff = date.today() - timedelta(days=args.retain_weeks * 7)
        before = len(deduped)
        deduped = [
            x for x in deduped
            if x.get("date") and date.fromisoformat(x["date"]) >= retain_cutoff
        ]
        if before != len(deduped):
            print(f"🗑️  retention: {args.retain_weeks}週より古い {before - len(deduped)} 件を整理")
        # broadcast_meta も同期で整理
        for show_key in list(broadcast_meta.keys()):
            broadcast_meta[show_key] = {
                d: m for d, m in broadcast_meta[show_key].items()
                if date.fromisoformat(d) >= retain_cutoff
            }

    print(f"\n✅ 合計 {len(deduped)} 件、{args.out} に保存（重複除去後）")
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "source": "tokyofukubukuro.com weekly + NHK公式 (api.web.nhk)",
            "broadcast_meta": broadcast_meta,
            "items": deduped,
        }, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
