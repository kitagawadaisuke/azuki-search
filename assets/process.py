#!/usr/bin/env python3
"""キャラクター画像の処理スクリプト
- 元画像からヘッダー用の小さいサムネイル生成
- 背景が白い場合は自動で透過処理
- アプリアイコンの土台としても使う"""
from PIL import Image
from pathlib import Path

ASSETS = Path(__file__).parent

def remove_white_bg(img: Image.Image, threshold: int = 240) -> Image.Image:
    """白に近いピクセルを透明化"""
    img = img.convert("RGBA")
    data = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = data[x, y]
            if r >= threshold and g >= threshold and b >= threshold:
                data[x, y] = (r, g, b, 0)
    return img


def trim_and_resize(src: Path, dst: Path, target_h: int = 240):
    """キャラ画像を透過化しつつ、不透明部分でクロップしてリサイズ"""
    im = Image.open(src).convert("RGBA")
    im = remove_white_bg(im)
    bbox = im.getbbox()
    if bbox:
        im = im.crop(bbox)
    w, h = im.size
    new_w = int(w * target_h / h)
    im = im.resize((new_w, target_h), Image.LANCZOS)
    im.save(dst, optimize=True)
    print(f"  ✅ {dst.name}  {im.size}")


def main():
    # ヘッダー表示用の小さいサムネイル
    trim_and_resize(ASSETS / "azuki-pose.png", ASSETS / "azuki-pose-thumb.png", target_h=240)
    trim_and_resize(ASSETS / "azuki-scene.png", ASSETS / "azuki-scene-thumb.png", target_h=240)


if __name__ == "__main__":
    main()
