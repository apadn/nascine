#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 nascine 品牌图标一览图（交付用）。"""

import os
import sys

from PIL import Image, ImageDraw, ImageFont, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, "..", "rootfs", "nas-tools", "web", "static", "img")
ICO = os.path.join(os.path.dirname(IMG), "favicon.ico")

LIGHT_BG = (245, 245, 247)
DARK_BG = (22, 22, 24)
CARD = (255, 255, 255)
TEXT = (29, 29, 31)
SUB = (134, 134, 139)
LINE = (224, 224, 228)

W, H = 1600, 980
PAD = 60

FONT_PATHS = [
    ("/System/Library/Fonts/Hiragino Sans GB.ttc", 0),
    ("/System/Library/Fonts/STHeiti Medium.ttc", 0),
    ("/System/Library/Fonts/Supplemental/Songti.ttc", 0),
]


def font(size):
    for path, idx in FONT_PATHS:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size, index=idx)
            except Exception:
                continue
    return ImageFont.load_default()


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "brand-sheet.png"
    app = Image.open(os.path.join(IMG, "logo.png")).convert("RGBA")
    mark = Image.open(os.path.join(IMG, "logo-mark.png")).convert("RGBA")
    splash = Image.open(os.path.join(IMG, "splash", "apple-splash-1170-2532.png"))
    ico = Image.open(ICO)
    ico.size = (64, 64)
    ico.load()
    ico = ico.convert("RGBA")

    sheet = Image.new("RGB", (W, H), LIGHT_BG)
    d = ImageDraw.Draw(sheet)

    d.text((PAD, 44), "nascine", font=font(44), fill=TEXT)
    d.text((PAD + 196, 66), "品牌图标", font=font(20), fill=SUB)
    d.text((PAD, 108), "iOS 超椭圆底 + 白色播放三角与镜头环｜矢量母版 1024px，全部栅格由母版一次缩放",
           font=font(15), fill=SUB)

    # ---- 主图标 + 尺寸梯度
    big = app.resize((280, 280), Image.LANCZOS)
    sheet.paste(big, (PAD, 160), big)
    d.text((PAD, 452), "应用图标 512px（母版 1024）", font=font(13), fill=SUB)

    d.text((400, 168), "尺寸梯度", font=font(15), fill=SUB)
    base_y = 440
    x = 400
    for size in (256, 128, 64, 32, 16):
        art = app.resize((size, size), Image.LANCZOS)
        sheet.paste(art, (x, base_y - size), art)
        d.text((x, base_y + 14), "%dpx" % size, font=font(12), fill=SUB)
        x += size + 26

    # ---- 分隔线
    d.line([(PAD, 520), (W - PAD, 520)], fill=LINE, width=1)

    # ---- 卡片一：浅色下的 favicon 与侧栏符号
    c1 = (PAD, 556, PAD + 420, 556 + 230)
    d.rounded_rectangle(c1, 16, fill=CARD)
    d.text((c1[0] + 24, c1[1] + 20), "favicon 与侧栏符号", font=font(14), fill=TEXT)
    sheet.paste(ico.resize((56, 56), Image.LANCZOS), (c1[0] + 26, c1[1] + 68))
    d.text((c1[0] + 26, c1[1] + 136), "favicon.ico\n16/32/48/64", font=font(12), fill=SUB)
    mk = mark.resize((54, 54), Image.LANCZOS)
    sheet.paste(mk, (c1[0] + 150, c1[1] + 68), mk)
    d.text((c1[0] + 150, c1[1] + 136), "logo-mark.png\n透明底 · 深色反白", font=font(12), fill=SUB)

    # ---- 卡片二：深色侧栏预览
    c2 = (PAD + 452, 556, PAD + 452 + 470, 556 + 230)
    d.rounded_rectangle(c2, 16, fill=DARK_BG)
    ia = app.resize((84, 84), Image.LANCZOS)
    sheet.paste(ia, (c2[0] + 34, c2[1] + 66), ia)
    inv = ImageOps.invert(mark.convert("RGB")).convert("RGBA")
    inv.putalpha(mark.split()[3])
    invr = inv.resize((40, 40), Image.LANCZOS)
    sheet.paste(invr, (c2[0] + 152, c2[1] + 88), invr)
    d.text((c2[0] + 210, c2[1] + 84), "nascine", font=font(24), fill=(245, 245, 247))
    d.text((c2[0] + 210, c2[1] + 118), "影音库中枢", font=font(13), fill=(152, 152, 157))
    d.text((c2[0] + 34, c2[1] + 186), "深色主题：符号反白，图标保持原色", font=font(12), fill=(152, 152, 157))

    # ---- iOS 启动图
    sp = splash.resize((146, 304), Image.LANCZOS)
    sheet.paste(sp, (PAD + 962, 556))
    d.text((PAD + 962, 876), "iOS 启动图 · 26 张", font=font(12), fill=SUB)

    # ---- 说明
    d.text((PAD, 812), "favicon.ico：16 / 32 / 48 / 64 多尺寸",
           font=font(13), fill=SUB)
    d.text((PAD, 838), "apple-touch-icon：128 → 1024 共 11 个尺寸",
           font=font(13), fill=SUB)
    d.text((PAD, 864), "PWA maskable：全幅底 + 缩小符号，避免被裁角",
           font=font(13), fill=SUB)

    sheet.save(out)
    print("->", out)


if __name__ == "__main__":
    main()
