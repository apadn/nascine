#!/usr/bin/env python3
"""在 apple 镜像之上追加第 9 层：移除 探索 / 资源搜索 / 订阅管理 三块功能。

改动：
  * 导航栏删除「探索」「资源搜索」「订阅管理」三个入口
  * 删除页面路由 /search /movie_rss /tv_rss /rss_history /rss_calendar
    /recommend /ranking /douban_movie /douban_tv /tmdb_movie /tmdb_tv
    /bangumi /media_detail /discovery_person /user_rss /rss_parser
  * 删除模板 search.html / discovery/ / rss/；近期下载改用 download/downloaded.html
  * 顶栏去掉资源搜索输入框，仅保留用户菜单
  * 媒体信息弹窗只保留「关闭」；服务页去掉 RSS 缓存清理
  * 系统设置-用户权限去掉三项
"""
import hashlib
import json
import os
import secrets
import shutil
import tarfile
import time

ROOT = "/Users/x/WorkBuddy/2026-10-21-21-08-51/nastools"
LAYERS = os.path.join(ROOT, "layers5")
STAGE = os.path.join(ROOT, "stage5")
APP = os.path.join(ROOT, "rootfs", "nas-tools")

manifest = json.load(open(os.path.join(LAYERS, "manifest.json"), encoding="utf-8"))
CFG = manifest[0]["Config"]
OLD_DIRS = [l.split("/")[0] for l in manifest[0]["Layers"]]
TOP_ID = OLD_DIRS[-1]

CHANGED = [
    "web/main.py",
    "web/apiv1.py",
    "web/action.py",
    "web/backend/user.py",
    "web/static/components/layout/navbar/index.js",
    "web/static/components/layout/searchbar/index.js",
    "web/templates/download/downloaded.html",
    "web/templates/navigation.html",
    "web/templates/service.html",
    "web/templates/setting/users.html",
]

# 目录 whiteout 用 .wh.<name>，文件 whiteout 用 .wh.<filename>
DELETED = [
    "web/templates/search.html",
    "web/templates/discovery",
    "web/templates/rss",
]

shutil.rmtree(STAGE, ignore_errors=True)
os.makedirs(STAGE)

new_id = secrets.token_hex(32)
new_dir = os.path.join(STAGE, new_id)
os.makedirs(new_dir)
layer_tar = os.path.join(new_dir, "layer.tar")
mtime = int(time.time())


def dir_entry(name):
    ti = tarfile.TarInfo(name)
    ti.type = tarfile.DIRTYPE
    ti.mode = 0o755
    ti.uid = ti.gid = 0
    ti.uname = ti.gname = "root"
    ti.mtime = mtime
    return ti


def file_entry(name, data=b""):
    ti = tarfile.TarInfo(name)
    ti.size = len(data)
    ti.mode = 0o644
    ti.uid = ti.gid = 0
    ti.uname = ti.gname = "root"
    ti.mtime = mtime
    import io
    return ti, io.BytesIO(data)


with tarfile.open(layer_tar, "w", format=tarfile.PAX_FORMAT) as tf:
    added_dirs = set()

    def ensure_parents(rel):
        parts = rel.split("/")
        for i in range(1, len(parts)):
            d = "nas-tools/" + "/".join(parts[:i]) + "/"
            if d not in added_dirs:
                added_dirs.add(d)
                tf.addfile(dir_entry(d))

    for rel in sorted(CHANGED):
        src = os.path.join(APP, rel)
        assert os.path.isfile(src), src
        ensure_parents(rel)
        ti = tf.gettarinfo(src, arcname="nas-tools/" + rel)
        ti.uid = ti.gid = 0
        ti.uname = ti.gname = "root"
        ti.mode = 0o644
        ti.mtime = mtime
        with open(src, "rb") as fh:
            tf.addfile(ti, fh)

    for rel in DELETED:
        ensure_parents(rel)
        parent, name = rel.rsplit("/", 1)
        ti, buf = file_entry("nas-tools/%s/.wh.%s" % (parent, name))
        tf.addfile(ti, buf)

with open(layer_tar, "rb") as fh:
    data = fh.read()
diff_id = hashlib.sha256(data).hexdigest()
print("new layer dir:", new_id)
print("new diff_id  :", diff_id)
print("layer size   : %.1f KB" % (len(data) / 1024))

top_meta = json.load(open(os.path.join(LAYERS, TOP_ID, "json"), encoding="utf-8"))
meta = dict(top_meta)
meta["id"] = new_id
meta["parent"] = TOP_ID
meta["created"] = time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
json.dump(meta, open(os.path.join(new_dir, "json"), "w", encoding="utf-8"),
          ensure_ascii=False, separators=(",", ":"))
open(os.path.join(new_dir, "VERSION"), "w").write("1.0")

cfg = json.load(open(os.path.join(LAYERS, CFG), encoding="utf-8"))
cfg["rootfs"]["diff_ids"].append("sha256:" + diff_id)
cfg["history"].append({
    "created": meta["created"],
    "created_by": "REMOVE discovery / resource-search / subscription modules",
    "comment": "remove-discovery-search-rss",
})
json.dump(cfg, open(os.path.join(STAGE, CFG), "w", encoding="utf-8"),
          ensure_ascii=False, separators=(",", ":"))

manifest[0]["Layers"].append("%s/layer.tar" % new_id)
json.dump(manifest, open(os.path.join(STAGE, "manifest.json"), "w", encoding="utf-8"),
          ensure_ascii=False, separators=(",", ":"))

for d in OLD_DIRS:
    dst = os.path.join(STAGE, d)
    os.makedirs(dst, exist_ok=True)
    for f in os.listdir(os.path.join(LAYERS, d)):
        os.link(os.path.join(LAYERS, d, f), os.path.join(dst, f))

json.dump({"syly948/nastools": {"2.9.1-apple": new_id}},
          open(os.path.join(STAGE, "repositories"), "w", encoding="utf-8"),
          separators=(",", ":"))
print("stage ready:", STAGE)
