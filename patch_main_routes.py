#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 web/main.py 精确删除 探索/资源搜索/订阅管理 的路由，并去掉服务页 RSS 缓存按钮。"""
import os
import re

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rootfs/nas-tools")
p = os.path.join(ROOT, "web/main.py")
lines = open(p, encoding="utf-8").read().split("\n")

ROUTES = ["/search", "/movie_rss", "/tv_rss", "/rss_history", "/rss_calendar",
          "/recommend", "/ranking", "/douban_movie", "/douban_tv",
          "/tmdb_movie", "/tmdb_tv", "/bangumi", "/media_detail",
          "/discovery_person", "/user_rss", "/rss_parser"]
removed, missing = [], []

for route in ROUTES:
    idx = next((i for i, l in enumerate(lines) if l.startswith("@App.route('%s'" % route)), None)
    if idx is None:
        missing.append(route)
        continue
    start = idx
    while start > 0 and lines[start - 1].startswith("# "):
        start -= 1
    # 下一个路由/错误处理器的起始行即上界（不含）
    end = next((j for j in range(idx + 1, len(lines))
                if lines[j].startswith("@App.route(") or lines[j].startswith("@App.errorhandler")),
               len(lines))
    # 回退掉尾部空行，保留一个分隔空行
    while end > start and lines[end - 1].strip() == "":
        end -= 1
    del lines[start:end]
    removed.append(route)

src = "\n".join(lines)
btn = re.search(r"\n    # 清理RSS缓存\n.*?'color': 'purple'\}\)\n", src, re.S)
if btn:
    src = src[:btn.start()] + "\n" + src[btn.end():]
    print("已删除服务页「清理RSS缓存」按钮")

open(p, "w", encoding="utf-8").write(src)
print("删除路由 %d: %s" % (len(removed), " ".join(removed)))
if missing:
    print("未找到:", missing)
print("剩余路由数:", src.count("@App.route("))
