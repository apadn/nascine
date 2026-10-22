#!/usr/bin/env python3
"""在已有 apple 镜像之上再追加一层：移除 PT 相关页面 + 新增改动文件。
原有 5 层字节保持不变，只追加第 6 层（含 overlay whiteout 删除标记）。
"""
import hashlib, json, os, secrets, shutil, tarfile, time

ROOT = "/Users/x/WorkBuddy/2026-10-21-21-08-51/nastools"
LAYERS = os.path.join(ROOT, "layers")
STAGE = os.path.join(ROOT, "stage2")
APP = os.path.join(ROOT, "rootfs", "nas-tools")

CFG = "303ebcad2acd491570bbc63b269d35f322b4c8b247170cb8590f5816d4ac71cb.json"
TOP_ID = "50bf9df0b2ebda3f059d096f47ad1c1e30743df76904a5c969cdeb232cef4e06"
OLD_DIRS = [
    "c60b71f37b1c2cd3ea6c7b91e2557f8543c670796311c46cdccfafb7f455a091",
    "d24e6742dbbe007a62d62e63e20cd26eadf10ada89632cce70040fb83b6a8f18",
    "1ab6236f646ad6c28802ea9a1a4626963982a8ae239e6503b533e8bcbf8e50ac",
    "8c558b0aa054ece0945e5eb2e06152de02d6cd258b7ca1da94dc2b8d265fff6f",
    TOP_ID,
]

# 需要写入这一层的文件（相对 /nas-tools）
CHANGED = [
    "web/static/css/apple.css",
    "web/templates/navigation.html",
    "web/templates/login.html",
    "web/templates/404.html",
    "web/templates/500.html",
    "web/templates/test.html",
    "web/static/components/layout/navbar/index.js",
    "web/static/components/layout/searchbar/index.js",
    "web/templates/setting/users.html",
    "web/backend/user.py",
    "web/main.py",
]

# 需要删除的路径（相对 /nas-tools），目录用 .wh.<name>
DELETED = [
    "web/templates/site",
    "web/templates/download/torrent_remove.html",
    "web/templates/download/userdownloader.html",
    "web/templates/setting/indexer.html",
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
        ti.mtime = mtime
        with open(src, "rb") as fh:
            tf.addfile(ti, fh)

    for rel in DELETED:
        assert not os.path.exists(os.path.join(APP, rel)), rel
        ensure_parents(rel)
        wname = "nas-tools/" + os.path.dirname(rel) + "/.wh." + os.path.basename(rel)
        ti = tarfile.TarInfo(wname)
        ti.size = 0
        ti.mode = 0o644
        ti.uid = ti.gid = 0
        ti.uname = ti.gname = "root"
        ti.mtime = mtime
        tf.addfile(ti)

with open(layer_tar, "rb") as fh:
    data = fh.read()
diff_id = hashlib.sha256(data).hexdigest()
print("new layer dir:", new_id)
print("new diff_id  :", diff_id)
print("layer size   :", f"{len(data)/1024:.1f} KB")

# ---- 层元数据 ----
top_meta = json.load(open(os.path.join(LAYERS, TOP_ID, "json"), encoding="utf-8"))
meta = dict(top_meta)
meta["id"] = new_id
meta["parent"] = TOP_ID
meta["created"] = time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
json.dump(meta, open(os.path.join(new_dir, "json"), "w", encoding="utf-8"),
          ensure_ascii=False, separators=(",", ":"))
open(os.path.join(new_dir, "VERSION"), "w").write("1.0")

# ---- config ----
cfg = json.load(open(os.path.join(LAYERS, CFG), encoding="utf-8"))
cfg["rootfs"]["diff_ids"].append("sha256:" + diff_id)
cfg["history"].append({
    "created": meta["created"],
    "created_by": "MOD remove PT pages: site/sitelist/resources/statistics/brushtask/torrent_remove/indexer",
    "comment": "remove-pt",
})
json.dump(cfg, open(os.path.join(STAGE, CFG), "w", encoding="utf-8"),
          ensure_ascii=False, separators=(",", ":"))

# ---- manifest ----
manifest = json.load(open(os.path.join(LAYERS, "manifest.json"), encoding="utf-8"))
manifest[0]["Layers"].append(f"{new_id}/layer.tar")
json.dump(manifest, open(os.path.join(STAGE, "manifest.json"), "w", encoding="utf-8"),
          ensure_ascii=False, separators=(",", ":"))

# ---- 硬链接旧层 ----
for d in OLD_DIRS:
    dst = os.path.join(STAGE, d)
    os.makedirs(dst, exist_ok=True)
    for f in os.listdir(os.path.join(LAYERS, d)):
        os.link(os.path.join(LAYERS, d, f), os.path.join(dst, f))

json.dump({"syly948/nastools": {"2.9.1-apple": new_id}},
          open(os.path.join(STAGE, "repositories"), "w", encoding="utf-8"),
          separators=(",", ":"))
print("stage ready:", STAGE)
