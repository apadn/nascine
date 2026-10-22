#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""移除 探索 / 资源搜索 / 订阅管理 三块功能的页面与入口（保留底层引擎）。"""
import os
import re
import shutil
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rootfs/nas-tools")
report = []


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def write(p, s):
    with open(p, "w", encoding="utf-8") as f:
        f.write(s)


# ---------------------------------------------------------------- navbar
def remove_nav_object(src, name):
    lines = src.split("\n")
    for i in range(len(lines) - 1):
        if lines[i] == "  {" and lines[i + 1].strip() == 'name: "%s",' % name:
            for j in range(i + 1, len(lines)):
                if lines[j] == "  },":
                    removed = j - i + 1
                    del lines[i:j + 1]
                    return "\n".join(lines), removed
    return src, 0


p = os.path.join(ROOT, "web/static/components/layout/navbar/index.js")
src = read(p)
for nm in ("探索", "资源搜索", "订阅管理"):
    src, n = remove_nav_object(src, nm)
    report.append("navbar 删除导航 %-6s 行数=%d" % (nm, n))
src = src.replace("      // 默认展开探索\n      setTimeout(() => { this.show_collapse(\"ranking\") }, 200);",
                  "      // 默认展开下载管理\n      setTimeout(() => { this.show_collapse(\"downloading\") }, 200);")
write(p, src)

# ---------------------------------------------------------------- searchbar
p = os.path.join(ROOT, "web/static/components/layout/searchbar/index.js")
src = read(p)
if "const search_source_icon" in src:
    src = re.sub(r"const search_source_icon = \{.*?\n\}\n\n", "", src, flags=re.S)
    report.append("searchbar 删除搜索源图标定义")
if "<!-- 搜索栏 -->" in src:
    start = src.index("<!-- 搜索栏 -->")
    end = src.index("<!-- 头像 -->")
    src = src[:start] + src[end:]
    report.append("searchbar 删除搜索输入框")
src = src.replace('    layout_search_source: { attribute: "layout-search-source" },\n', "")
src = src.replace('    _search_source: { state: true },\n', "")
src = src.replace('    this.layout_search_source = "tmdb";\n', "")
src = src.replace('    this._search_source = "tmdb";\n', "")
src = src.replace('    this._search_source = localStorage.getItem("SearchSource") ?? this.layout_search_source;\n', "")
write(p, src)

# ---------------------------------------------------------------- main.py 路由
p = os.path.join(ROOT, "web/main.py")
lines = read(p).split("\n")
ROUTES = ["/search", "/movie_rss", "/tv_rss", "/rss_history", "/rss_calendar",
          "/recommend", "/ranking", "/douban_movie", "/douban_tv",
          "/tmdb_movie", "/tmdb_tv", "/bangumi", "/media_detail",
          "/discovery_person", "/user_rss", "/rss_parser"]
removed_routes = []
for route in ROUTES:
    for i, l in enumerate(lines):
        if l.startswith("@App.route('%s'" % route):
            start = i
            while start > 0 and lines[start - 1].startswith("# "):
                start -= 1
            end = i
            for j in range(i + 1, len(lines)):
                if lines[j].startswith("@App.route(") or lines[j].startswith("@App.errorhandler"):
                    end = j
                    break
            else:
                end = len(lines)
            while end > start and lines[end - 1].strip() == "":
                end -= 1
            del lines[start:end + 1]
            removed_routes.append(route)
            break
report.append("main.py 删除路由 %d 个: %s" % (len(removed_routes), " ".join(removed_routes)))

src = "\n".join(lines)
# 服务页：清理 RSS 缓存按钮
btn = re.search(r"\n    # 清理RSS缓存\n.*?'color': 'purple'\}\)\n", src, re.S)
if btn:
    src = src[:btn.start()] + "\n" + src[btn.end():]
    report.append("main.py 删除服务页「清理RSS缓存」按钮")
write(p, src)

# ---------------------------------------------------------------- navigation.html
p = os.path.join(ROOT, "web/templates/navigation.html")
lines = read(p).split("\n")


def cut_modal(lines, modal_id):
    start = None
    for i, l in enumerate(lines):
        if re.match(r'^<div class="modal[^"]*" id="%s"' % modal_id, l):
            start = i
            break
    if start is None:
        return lines, 0
    depth = 0
    end = start
    for j in range(start, len(lines)):
        depth += len(re.findall(r"<div\b", lines[j]))
        depth -= len(re.findall(r"</div>", lines[j]))
        if j > start and depth == 0:
            end = j
            break
    n = end - start + 1
    del lines[start:end + 1]
    return lines, n


for mid in ("system-rss-seasons", "modal-manual-rss", "modal-search-advanced"):
    lines, n = cut_modal(lines, mid)
    report.append("navigation.html 删除弹窗 #%s 行数=%d" % (mid, n))

src = "\n".join(lines)

# 媒体弹窗：去掉 详情/订阅/搜索/刷新 按钮，仅留关闭
old_btns = re.search(r'        <div class="d-flex">\n          <a href="#" target="_blank" class="card-btn" id="system_media_url_btn">.*?        </div>\n', src, re.S)
if old_btns:
    new_btns = ('        <div class="d-flex">\n'
                '          <a href="javascript:void(0)" class="card-btn d-none d-md-block" data-bs-dismiss="modal">\n'
                '            关闭\n'
                '          </a>\n'
                '        </div>\n')
    src = src[:old_btns.start()] + new_btns + src[old_btns.end():]
    report.append("navigation.html 媒体弹窗保留「关闭」按钮")

# 媒体弹窗：去掉订阅/搜索/详情按钮的装配逻辑
start_marker = "        //订阅按钮、搜索按钮\n"
end_marker = '        $("#system_media_name_link").attr("href", ret.link_url);'
if start_marker in src and end_marker in src:
    a = src.index(start_marker)
    b = src.index(end_marker)
    src = src[:a] + src[b:]
    report.append("navigation.html 移除媒体弹窗订阅/搜索/详情装配逻辑")

# code==1 分支里对编辑订阅弹窗的调用
src = src.replace('''        if (ret.rssid) {
          show_edit_rss_media_modal(ret.rssid, ret.type_str);
        } else {
          show_fail_modal(`${name} 未查询到TMDB媒体信息！`);
        }''', '''        show_fail_modal(`${name} 未查询到TMDB媒体信息！`);''')

lines = src.split("\n")
FUNCS = ["media_search", "add_rss_media", "add_rss_manual", "remove_rss_media",
         "refresh_rss_media", "search_mediainfo_media", "show_add_rss_media_modal",
         "show_edit_rss_media_modal", "show_search_advanced_modal"]
cuts = []
for name in FUNCS:
    pat = re.compile(r"^  function %s\b" % re.escape(name))
    s = next((i for i, l in enumerate(lines) if pat.match(l)), None)
    if s is None:
        report.append("navigation.html 未找到函数 %s" % name)
        continue
    e = next((j for j in range(s + 1, len(lines)) if lines[j] == "  }"), None)
    if e is None:
        report.append("navigation.html 函数 %s 未闭合" % name)
        continue
    while s > 0 and lines[s - 1].strip().startswith("//"):
        s -= 1
    while e + 1 < len(lines) and lines[e + 1].strip() == "":
        e += 1
    cuts.append((s, e, name))
for s, e, name in sorted(cuts, reverse=True):
    del lines[s:e + 1]
    report.append("navigation.html 删除函数 %s (行 %d-%d)" % (name, s + 1, e + 1))
write(p, "\n".join(lines))

# ---------------------------------------------------------------- 权限项
p = os.path.join(ROOT, "web/templates/setting/users.html")
src = read(p)
for nm in ("资源搜索", "探索", "订阅管理"):
    blk = re.search(r'              <label class="form-selectgroup-item">\n'
                    r'                <input type="checkbox" name="user_pris" value="%s".*?</label>\n' % nm, src, re.S)
    if blk:
        src = src[:blk.start()] + src[blk.end():]
        report.append("users.html 删除权限项 %s" % nm)
write(p, src)

p = os.path.join(ROOT, "web/backend/user.py")
src = read(p)
if "资源搜索" in src:
    src = src.replace('"我的媒体库,资源搜索,探索,订阅管理,下载管理,媒体整理,服务,系统设置"',
                      '"我的媒体库,下载管理,媒体整理,服务,系统设置"')
    write(p, src)
    report.append("user.py 默认权限移除 资源搜索/探索/订阅管理")

# ---------------------------------------------------------------- service.html
p = os.path.join(ROOT, "web/templates/service.html")
lines = read(p).split("\n")
for i, l in enumerate(lines):
    if '} else if (id === "rsshistory") {' in l:
        depth = 0
        end = i
        for j in range(i, len(lines)):
            depth += lines[j].count("{") - lines[j].count("}")
            if depth == 0 and j > i:
                end = j
                break
        del lines[i:end + 1]
        report.append("service.html 删除 RSS 缓存分支")
        break
write(p, "\n".join(lines))

# ---------------------------------------------------------------- 删除模板
for rel in ("web/templates/search.html", "web/templates/discovery", "web/templates/rss"):
    t = os.path.join(ROOT, rel)
    if os.path.isdir(t):
        shutil.rmtree(t)
        report.append("删除目录 %s" % rel)
    elif os.path.isfile(t):
        os.remove(t)
        report.append("删除文件 %s" % rel)

print("\n".join(report))
