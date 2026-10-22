#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""nascine 品牌图标生成器。

从矢量定义直接产出一整套 Web 图标资源：
  ico / 16 / 32 / 512 / 832 / 1024 / maskable / apple-touch / splash

设计：iOS 式超椭圆（squircle）石墨渐变底 + 中央「播放三角 + 镜头环」。
所有栅格图都由 1024px 母版用 Lanczos 缩放，避免多次重采样发虚。

用法：
  python build_icons.py <web/static/img 目录>
"""

import math
import os
import subprocess
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
MASTER = 1024
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# 启动图底色
SPLASH_BG = (14, 14, 16)

# ---------------------------------------------------------------- 矢量


def squircle_path(size=1024, exponent=5.0, steps=720, inset=0.0):
    """超椭圆路径：iOS 图标即 |x|^n + |y|^n = 1 的连续曲率轮廓。"""
    r = size / 2.0 - inset
    cx = cy = size / 2.0
    pts = []
    for i in range(steps):
        t = 2 * math.pi * i / steps
        c, s = math.cos(t), math.sin(t)
        x = cx + r * math.copysign(abs(c) ** (2.0 / exponent), c)
        y = cy + r * math.copysign(abs(s) ** (2.0 / exponent), s)
        pts.append((x, y))
    d = "M%.2f,%.2f" % pts[0]
    d += "".join(" L%.2f,%.2f" % p for p in pts[1:])
    return d + " Z"


def glyph(scale=1.0, ring_opacity=0.14, color="#ffffff"):
    """播放三角 + 镜头环。三角用 round linejoin 描边取得圆角轮廓。"""
    cx = cy = 512.0
    ax, ay = 392.0, 346.0
    bx, by = 392.0, 678.0
    px, py = 664.0, 512.0
    sw = 72.0
    ring = ('<circle cx="%.1f" cy="%.1f" r="290" fill="none" stroke="%s" '
            'stroke-width="9" opacity="%.2f"/>') % (cx, cy, color, ring_opacity)
    tri = ('<path d="M%.1f,%.1f L%.1f,%.1f L%.1f,%.1f Z" fill="%s" stroke="%s" '
           'stroke-width="%.1f" stroke-linejoin="round" stroke-linecap="round"/>') % (
        ax, ay, bx, by, px, py, color, color, sw)
    return ('<g transform="translate(%.2f,%.2f) scale(%.4f) translate(%.2f,%.2f)">%s%s</g>'
            % (cx, cy, scale, -cx, -cy, ring, tri))


def icon_svg(square=False, glyph_scale=1.14):
    """应用图标。square=True 时铺满画布（PWA maskable 用，避免裁出透明角）。"""
    if square:
        bg_shape = '<rect x="0" y="0" width="1024" height="1024" fill="url(#bg)"/>'
    else:
        bg_shape = '<path d="%s" fill="url(#bg)"/>' % squircle_path(1024, 5.0, 720)
    return """<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024">
  <defs>
    <linearGradient id="bg" x1="0.18" y1="0" x2="0.82" y2="1">
      <stop offset="0" stop-color="#35353b"/>
      <stop offset="0.46" stop-color="#1f1f23"/>
      <stop offset="1" stop-color="#0c0c0e"/>
    </linearGradient>
    <radialGradient id="sheen" cx="0.28" cy="0.06" r="0.85">
      <stop offset="0" stop-color="#ffffff" stop-opacity="0.13"/>
      <stop offset="0.55" stop-color="#ffffff" stop-opacity="0.03"/>
      <stop offset="1" stop-color="#ffffff" stop-opacity="0"/>
    </radialGradient>
  </defs>
  %s
  <path d="%s" fill="url(#sheen)"/>
  <path d="%s" fill="none" stroke="#ffffff" stroke-width="3" opacity="0.10"/>
  %s
</svg>
""" % (bg_shape, squircle_path(1024, 5.0, 720),
       squircle_path(1024, 5.0, 720, inset=1.0), glyph(glyph_scale))


def mark_svg():
    """透明底单色符号，用于侧栏品牌位；深色主题由 CSS 反色。"""
    return """<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="320 268 420 488">
  <path d="M392,346 L392,678 L664,512 Z" fill="#1d1d1f" stroke="#1d1d1f"
        stroke-width="72" stroke-linejoin="round" stroke-linecap="round"/>
</svg>
"""


# ---------------------------------------------------------------- 渲染


def render_svg(svg_text, out_png, size=MASTER, transparent=True):
    """headless Chrome 精确栅格化（矢量渲染，无位图缩放损失）。"""
    tmp = os.path.join(HERE, "_render.html")
    inline = svg_text.replace('width="1024" height="1024" ', '')
    html = ("<!doctype html><meta charset=utf-8><style>html,body{margin:0;padding:0;"
            "overflow:hidden;background:transparent}#w svg{display:block;width:%dpx;"
            "height:%dpx}</style><div id=w>%s</div>") % (size, size, inline)
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(html)
    cmd = [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
           "--hide-scrollbars", "--disable-dev-shm-usage",
           "--user-data-dir=/tmp/nascine-icon-chrome",
           "--force-device-scale-factor=1",
           "--window-size=%d,%d" % (size, size),
           "--screenshot=" + out_png]
    if transparent:
        cmd.append("--default-background-color=00000000")
    cmd.append("file://" + tmp)
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.remove(tmp)
    return out_png


def scaled(src, size):
    return src.resize((size, size), Image.LANCZOS)


def main():
    img_dir = sys.argv[1]
    if not os.path.isdir(img_dir):
        raise SystemExit("目标目录不存在: " + img_dir)
    icons_dir = os.path.join(img_dir, "icons")
    splash_dir = os.path.join(img_dir, "splash")
    os.makedirs(icons_dir, exist_ok=True)
    os.makedirs(splash_dir, exist_ok=True)

    # 源文件归档（可直接给设计工具复用）
    open(os.path.join(HERE, "nascine-icon.svg"), "w", encoding="utf-8").write(icon_svg())
    open(os.path.join(HERE, "nascine-mark.svg"), "w", encoding="utf-8").write(mark_svg())

    app_png = os.path.join(HERE, "_app.png")
    mask_png = os.path.join(HERE, "_mask.png")
    mark_png = os.path.join(HERE, "_mark.png")
    render_svg(icon_svg(), app_png)
    render_svg(icon_svg(square=True, glyph_scale=0.86), mask_png)
    render_svg(mark_svg(), mark_png)

    app = Image.open(app_png).convert("RGBA")
    mask = Image.open(mask_png).convert("RGBA")
    mark = Image.open(mark_png).convert("RGBA")

    written = []

    def save(im, path, **kw):
        im.save(path, **kw)
        written.append(path)

    # 1. favicon（多尺寸 ICO）—— 放在 web/static 根目录，而不是 img/ 下
    save(app, os.path.join(os.path.dirname(img_dir), "favicon.ico"),
         format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])

    # 2. 主 logo 与自适应尺寸
    save(scaled(app, 512), os.path.join(img_dir, "logo.png"),
         optimize=True, compress_level=9)
    save(scaled(app, 512), os.path.join(img_dir, "logo-black.png"),
         optimize=True, compress_level=9)
    save(scaled(app, 256), os.path.join(img_dir, "logo-white.png"),
         optimize=True, compress_level=9)
    save(scaled(app, 32), os.path.join(img_dir, "logo-32x32.png"), optimize=True)
    save(scaled(app, 16), os.path.join(img_dir, "logo-16x16.png"), optimize=True)

    # 3. 侧栏品牌符号（透明底，深色主题反色）；logo-blue 是旧引用名，一并覆盖
    for name in ("logo-mark.png", "logo-blue.png"):
        save(scaled(mark, 256), os.path.join(img_dir, name), optimize=True)

    # 4. apple-touch / PWA maskable
    for size in (128, 144, 152, 167, 172, 180, 196, 216, 256, 512, 1024):
        save(scaled(mask, size), os.path.join(icons_dir, "%d.png" % size), optimize=True)
    save(scaled(mask, 196), os.path.join(icons_dir, "196_ALT.png"), optimize=True)
    save(scaled(mask, 512), os.path.join(icons_dir, "512_ALT.png"), optimize=True)

    # 5. iOS 启动图：纯色底 + 居中图标
    for fn in sorted(os.listdir(splash_dir)):
        if not fn.endswith(".png") or not fn.startswith("apple-splash-"):
            continue
        try:
            w, h = [int(v) for v in fn[len("apple-splash-"):-4].split("-")]
        except ValueError:
            continue
        canvas = Image.new("RGB", (w, h), SPLASH_BG)
        side = int(min(w, h) * 0.30)
        art = scaled(app, side)
        canvas.paste(art, ((w - side) // 2, (h - side) // 2), art)
        save(canvas, os.path.join(splash_dir, fn), optimize=True)

    # 6. 通用启动图（2048x2732）
    canvas = Image.new("RGB", (2048, 2732), SPLASH_BG)
    side = 560
    art = scaled(app, side)
    canvas.paste(art, ((2048 - side) // 2, (2732 - side) // 2), art)
    save(canvas, os.path.join(img_dir, "startup.jpg"), quality=92, optimize=True)

    for p in (app_png, mask_png, mark_png):
        os.remove(p)

    print("已生成 %d 个图标文件 -> %s" % (len(written), img_dir))
    for p in written:
        print("  ", os.path.relpath(p, img_dir))


if __name__ == "__main__":
    main()
