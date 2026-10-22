#!/usr/bin/env python3
"""在 apple 镜像之上再追加第 7 层：修复 Unraid/FUSE 下目录同步不自动触发的问题。

改动内容：
  app/sync.py
    1. 监控目录位于 FUSE 挂载（Unraid /mnt/user = fuse.shfs）时自动降级为轮询监控，
       解决其它容器写入后收不到 inotify 事件、必须手动点「立即同步」才转移的问题；
    2. 转移失败后按 60s/120s 退避重试最多 3 次，避免下载器校验中、文件仍在写入导致的
       一次性失败被永久丢弃（表现为「必须手动再点一次」）；
    3. 失败的队列项不再无限堆积。

原有 6 层字节保持不变，只追加第 7 层。
"""
import hashlib, json, os, secrets, shutil, tarfile, time

ROOT = "/Users/x/WorkBuddy/2026-10-21-21-08-51/nastools"
LAYERS = os.path.join(ROOT, "layers2")
STAGE = os.path.join(ROOT, "stage3")
APP = os.path.join(ROOT, "rootfs", "nas-tools")

manifest = json.load(open(os.path.join(LAYERS, "manifest.json"), encoding="utf-8"))
CFG = manifest[0]["Config"]
OLD_DIRS = [l.split("/")[0] for l in manifest[0]["Layers"]]
TOP_ID = OLD_DIRS[-1]

CHANGED = [
    "app/sync.py",
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
        ti.mode = 0o644
        ti.mtime = mtime
        with open(src, "rb") as fh:
            tf.addfile(ti, fh)

with open(layer_tar, "rb") as fh:
    data = fh.read()
diff_id = hashlib.sha256(data).hexdigest()
print("new layer dir:", new_id)
print("new diff_id  :", diff_id)
print("layer size   : %.1f KB" % (len(data) / 1024))

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
    "created_by": "FIX sync: auto polling on FUSE mounts (Unraid /mnt/user) + retry failed transfers",
    "comment": "fix-sync-fuse",
})
json.dump(cfg, open(os.path.join(STAGE, CFG), "w", encoding="utf-8"),
          ensure_ascii=False, separators=(",", ":"))

# ---- manifest ----
manifest[0]["Layers"].append("%s/layer.tar" % new_id)
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
