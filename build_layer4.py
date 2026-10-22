#!/usr/bin/env python3
"""在 apple 镜像之上追加第 8 层：修正探索页海报卡圆角与悬停文字排版。

改动内容（web/static/css/apple.css）：
  1. .lit-normal-card / .lit-person-card 圆角由 14px 改为 18px（与内部
     img.card-img / .card-img-overlay 的 rounded-4 一致），修复海报四角露白；
  2. 小屏媒体查询里给海报卡加同样的 18px 例外；
  3. 恢复 .card-sm 的紧凑内距，避免 135px 宽海报的悬停文字被挤成窄条；
  4. 海报描边由写死的 1px #888 改为跟随主题的发丝线，深色模式不再刺眼。
"""
import hashlib, json, os, secrets, shutil, tarfile, time

ROOT = "/Users/x/WorkBuddy/2026-10-21-21-08-51/nastools"
LAYERS = os.path.join(ROOT, "layers3")
STAGE = os.path.join(ROOT, "stage4")
APP = os.path.join(ROOT, "rootfs", "nas-tools")

manifest = json.load(open(os.path.join(LAYERS, "manifest.json"), encoding="utf-8"))
CFG = manifest[0]["Config"]
OLD_DIRS = [l.split("/")[0] for l in manifest[0]["Layers"]]
TOP_ID = OLD_DIRS[-1]

CHANGED = [
    "web/static/css/apple.css",
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
    "created_by": "FIX poster cards: align card radius with img (18px) + compact overlay padding",
    "comment": "fix-poster-card",
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
