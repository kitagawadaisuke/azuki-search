#!/usr/bin/env python3
"""
AppIcon (1024x1024 PNG) を Pillow で生成する。
mockupのTVマスコット(青いTV+顔+アンテナ) を踏襲。

使い方:
    python3 ios/scripts/gen_app_icon.py
    → ios/AzukiSearch/Assets.xcassets/AppIcon.appiconset/icon-1024.png
"""
from PIL import Image, ImageDraw, ImageFilter
from pathlib import Path

OUT = Path(__file__).parent.parent / "AzukiSearch" / "Assets.xcassets" / "AppIcon.appiconset" / "icon-1024.png"

SIZE = 1024
# パステルなクリーム背景
BG_TOP    = (255, 247, 236)
BG_BOTTOM = (255, 232, 212)
TV_BLUE_1 = (158, 218, 240)
TV_BLUE_2 = (115, 199, 232)
SCREEN_BG = (255, 247, 235)
ACCENT_ORANGE = (255, 165, 102)
EYE_DARK  = (50, 38, 30)
CHEEK     = (255, 178, 199)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def make_bg(size):
    img = Image.new("RGB", (size, size), BG_TOP)
    px = img.load()
    for y in range(size):
        t = y / (size - 1)
        c = lerp(BG_TOP, BG_BOTTOM, t)
        for x in range(size):
            px[x, y] = c
    return img


def main():
    img = make_bg(SIZE)
    d = ImageDraw.Draw(img, "RGBA")

    # === 中央タイル(青グラデの角丸) ===
    pad = SIZE * 0.14
    tile_box = (pad, pad + SIZE * 0.04, SIZE - pad, SIZE - pad + SIZE * 0.04)
    radius = SIZE * 0.16

    # グラデ tile はマスクで合成
    grad = Image.new("RGB", (int(tile_box[2] - tile_box[0]), int(tile_box[3] - tile_box[1])), TV_BLUE_1)
    gp = grad.load()
    for y in range(grad.height):
        t = y / max(grad.height - 1, 1)
        c = lerp(TV_BLUE_1, TV_BLUE_2, t)
        for x in range(grad.width):
            gp[x, y] = c
    mask = Image.new("L", grad.size, 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle((0, 0, grad.width - 1, grad.height - 1), radius=radius, fill=255)
    img.paste(grad, (int(tile_box[0]), int(tile_box[1])), mask)

    # === 内側 screen (オフホワイトの角丸) ===
    inset = SIZE * 0.07
    screen_box = (
        tile_box[0] + inset, tile_box[1] + inset * 1.3,
        tile_box[2] - inset, tile_box[3] - inset * 0.7,
    )
    d.rounded_rectangle(screen_box, radius=radius * 0.7, fill=SCREEN_BG)

    # === アンテナ ===
    cx = SIZE / 2
    ant_top_y = pad - SIZE * 0.04
    ant_left_x = SIZE * 0.34
    ant_right_x = SIZE * 0.66
    base_y = pad + SIZE * 0.04
    line_w = int(SIZE * 0.018)
    d.line([(SIZE * 0.40, base_y + SIZE * 0.02), (ant_left_x - SIZE * 0.02, ant_top_y)], fill=TV_BLUE_2, width=line_w)
    d.line([(SIZE * 0.60, base_y + SIZE * 0.02), (ant_right_x + SIZE * 0.02, ant_top_y)], fill=TV_BLUE_2, width=line_w)
    # オレンジドット
    r_dot = SIZE * 0.05
    d.ellipse([(ant_left_x - r_dot, ant_top_y - r_dot), (ant_left_x + r_dot, ant_top_y + r_dot)], fill=ACCENT_ORANGE)
    d.ellipse([(ant_right_x - r_dot, ant_top_y - r_dot), (ant_right_x + r_dot, ant_top_y + r_dot)], fill=ACCENT_ORANGE)

    # === 顔 (目 + 口 + ほっぺ) ===
    eye_y = (screen_box[1] + screen_box[3]) / 2 - SIZE * 0.04
    eye_dx = SIZE * 0.10
    eye_r  = SIZE * 0.04
    d.ellipse([(cx - eye_dx - eye_r, eye_y - eye_r), (cx - eye_dx + eye_r, eye_y + eye_r)], fill=EYE_DARK)
    d.ellipse([(cx + eye_dx - eye_r, eye_y - eye_r), (cx + eye_dx + eye_r, eye_y + eye_r)], fill=EYE_DARK)

    # 口 (にっこりカーブ)
    mouth_y = eye_y + SIZE * 0.10
    mouth_w = SIZE * 0.16
    mouth_h = SIZE * 0.07
    bbox = (cx - mouth_w / 2, mouth_y - mouth_h, cx + mouth_w / 2, mouth_y + mouth_h)
    d.arc(bbox, start=20, end=160, fill=EYE_DARK, width=int(SIZE * 0.014))

    # ほっぺ
    cheek_y = mouth_y - SIZE * 0.01
    cheek_dx = SIZE * 0.20
    cheek_r = SIZE * 0.035
    d.ellipse([(cx - cheek_dx - cheek_r, cheek_y - cheek_r), (cx - cheek_dx + cheek_r, cheek_y + cheek_r)], fill=CHEEK)
    d.ellipse([(cx + cheek_dx - cheek_r, cheek_y - cheek_r), (cx + cheek_dx + cheek_r, cheek_y + cheek_r)], fill=CHEEK)

    # === 微小ハイライト (光沢感) ===
    hl_box = (tile_box[0] + SIZE * 0.05, tile_box[1] + SIZE * 0.04, tile_box[2] - SIZE * 0.55, tile_box[1] + SIZE * 0.10)
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rounded_rectangle(hl_box, radius=20, fill=(255, 255, 255, 70))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, format="PNG", optimize=True)
    print(f"✅ wrote {OUT} ({SIZE}x{SIZE})")


if __name__ == "__main__":
    main()
