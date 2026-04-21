#!/usr/bin/env python3
"""アプリアイコン生成（PWA + iOS用）"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import sys

OUT = Path("icons")
OUT.mkdir(exist_ok=True)

# 背景色（あたたかいEテレ感：クリーム + アクセントカラー）
BG = (255, 247, 232)        # クリーム
ACCENT = (255, 138, 61)      # あたたかオレンジ
ACCENT2 = (255, 95, 156)     # いちごピンク
TEXT = (61, 40, 23)          # 濃茶


def find_jp_font(size: int):
    """日本語フォントを探して返す（macOS優先）"""
    candidates = [
        "/System/Library/Fonts/ヒラギノ角ゴシック W8.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        "/System/Library/Fonts/Apple Color Emoji.ttc",
    ]
    for p in candidates:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def make_icon(size: int, maskable: bool = False) -> Image.Image:
    img = Image.new("RGB", (size, size), BG)
    draw = ImageDraw.Draw(img)

    cx, cy = size / 2, size / 2
    pad = size * 0.1 if maskable else 0
    inner = size - 2 * pad

    # 角丸正方形の温かいオレンジ背景
    bg_r = inner * 0.5
    draw.rounded_rectangle(
        [cx - bg_r, cy - bg_r, cx + bg_r, cy + bg_r],
        radius=int(size * 0.2),
        fill=ACCENT,
    )

    # 中央テキスト「あ」
    font_size = int(inner * 0.52)
    font = find_jp_font(font_size)
    text = "あ"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (size - tw) / 2 - bbox[0]
    ty = (size - th) / 2 - bbox[1] - size * 0.01
    draw.text((tx, ty), text, font=font, fill=(255, 255, 255))

    # 下部にちいさなピンクの●●●（リズム的ドット）
    dot_r = size * 0.025
    dot_y = cy + inner * 0.32
    gap = dot_r * 3
    for i, color in enumerate([(255, 255, 255, 230), ACCENT2, (255, 255, 255, 230)]):
        x = cx + (i - 1) * gap
        draw.ellipse([x - dot_r, dot_y - dot_r, x + dot_r, dot_y + dot_r], fill=color[:3] if len(color)==4 else color)

    return img


def main():
    sizes = [
        (192, "icon-192.png", False),
        (512, "icon-512.png", False),
        (512, "icon-512-maskable.png", True),
        (180, "apple-touch-icon.png", False),  # iOS
        (32,  "favicon-32.png", False),
        (16,  "favicon-16.png", False),
    ]
    for size, name, maskable in sizes:
        img = make_icon(size, maskable=maskable)
        img.save(OUT / name, optimize=True)
        print(f"  ✅ {OUT / name}  ({size}x{size}{' maskable' if maskable else ''})")


if __name__ == "__main__":
    main()
