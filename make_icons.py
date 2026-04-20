#!/usr/bin/env python3
"""アプリアイコン生成（PWA + iOS用）"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import sys

OUT = Path("icons")
OUT.mkdir(exist_ok=True)

# 背景色（アプリのテーマカラーに合わせる：dark navy + accent orange）
BG = (15, 20, 25)
ACCENT = (255, 184, 77)
ACCENT2 = (255, 107, 157)


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

    # 角丸風グラデーション背景（中央が少し明るい）
    cx, cy = size / 2, size / 2
    radius = size * 0.45
    # アクセント円をぼかして配置（光るドット風）
    for r, color in [(radius * 1.0, (35, 42, 61)), (radius * 0.65, (50, 60, 85))]:
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)

    # 中央テキスト「E」+ 検索アイコン的な雰囲気
    pad = size * 0.08 if maskable else 0
    inner = size - 2 * pad

    # 大きな「E」を描く
    font_size = int(inner * 0.55)
    font = find_jp_font(font_size)
    text = "E"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (size - tw) / 2 - bbox[0]
    ty = (size - th) / 2 - bbox[1] - size * 0.05
    draw.text((tx, ty), text, font=font, fill=ACCENT)

    # 下に小さく「テレ」
    sub_size = int(inner * 0.13)
    sub_font = find_jp_font(sub_size)
    sub = "テレ"
    sb = draw.textbbox((0, 0), sub, font=sub_font)
    sw = sb[2] - sb[0]
    sh = sb[3] - sb[1]
    draw.text(((size - sw) / 2 - sb[0], size * 0.72 - sb[1]), sub, font=sub_font, fill=(255, 255, 255))

    # 検索アイコン的な小さな丸（右下）
    dot_r = size * 0.06
    draw.ellipse([size - dot_r * 3.5, size - dot_r * 3.5, size - dot_r * 0.8, size - dot_r * 0.8],
                 outline=ACCENT2, width=max(2, int(size * 0.012)))

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
