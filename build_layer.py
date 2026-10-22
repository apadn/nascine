#!/usr/bin/env python3
# 用「追加一层」的方式重建 docker save 镜像包（保持原 4 层字节不变）
import hashlib, io, json, os, shutil, tarfile, time, secrets

ROOT = "/Users/x/WorkBuddy/2026-10-21-21-08-51/nastools"
LAYERS = os.path.join(ROOT, "layers")
STAGE = os.path.join(ROOT, "stage")
APP = os.path.join(ROOT, "rootfs", "nas-tools")

CFG = "303ebcad2acd491570bbc63b269d35f322b4c8b247170cb8590f5816d4ac71cb.json"
TOP_ID = "8c558b0aa054ece0945e5eb2e06152de02d6cd258b7ca1da94dc2b8d265fff6f"
OLD_DIRS = [
    "c60b71f37b1c2cd3ea6c7b91e2557f8543c670796311c46cdccfafb7f455a091",
    "d24e6742dbbe007a62d62e63e20cd26eadf10ada89632cce70040fb83b6a8f18",
    "1ab6236f646ad6c28802ea9a1a4626963982a8ae239e6503b533e8bcbf8e50ac",
    TOP_ID,
]
# 本次改动的文件（相对 /nas-tools）
CHANGED = [
    "web/static/css/apple.css",
    "web/templates/navigation.html",
    "web/templates/login.html",
    "web/templates/404.html",
    "web/templates/500.html",
    "web/templates/test.html",
    "web/static/components/layout/navbar/index.js",
    "web/static/components/layout/searchbar/index.js",
]

# ---------- 1. 生成新层 tar ----------
new_id = secrets.token_hex(32)
new_dir = os.path.join(STAGE, new_id)
os.makedirs(new_dir, exist_ok=True)
layer_tar = os.path.join(new_dir, "layer.tar")

mtime = int(time.time())
with tarfile.open(layer_tar, "w", format=tarfile.PAX_FORMAT) as tf:
    added_dirs = set()
    for rel in sorted(CHANGED):
        src = os.path.join(APP, rel)
        assert os.path.isfile(src), src
        parts = rel.split("/")
        for i in range(1, len(parts)):
            d = "nas-tools/" + "/".join(parts[:i]) + "/"
            if d not in added_dirs:
                added_dirs.add(d)
                ti = tarfile.TarInfo(d)
                ti.type = tarfile.DIRTYPE
                ti.mode = 0o755
                ti.uid = ti.gid = 0
                ti.uname = ti.gname = "root"
                ti.mtime = mtime
                tf.addfile(ti)
        ti = tf.gettarinfo(src, arcname="nas-tools/" + rel)
        ti.uid = ti.gid = 0
        ti.uname = ti.gname = "root"
        ti.mtime = mtime
        with open(src, "rb") as fh:
            tf.addfile(ti, fh)

with open(layer_tar, "rb") as fh:
    data = fh.read()
diff_id = hashlib.sha256(data).hexdigest()
print("new layer id :", new_id)
print("new diff_id  :", diff_id)
print("layer size   :", f"{len(data)/1024:.1f} KB")

# ---------- 2. 层元数据（legacy 格式，克隆顶层结构） ----------
top_meta = json.load(open(os.path.join(LAYERS, TOP_ID, "json"), encoding="utf-8"))
meta = dict(top_meta)
meta["id"] = new_id
meta["parent"] = TOP_ID
meta["created"] = time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
json.dump(meta, open(os.path.join(new_dir, "json"), "w", encoding="utf-8"),
          ensure_ascii=False, separators=(",", ":"))
open(os.path.join(new_dir, "VERSION"), "w").write("1.0")

# ---------- 3. 更新 config ----------
cfg = json.load(open(os.path.join(LAYERS, CFG), encoding="utf-8"))
cfg["rootfs"]["diff_ids"].append("sha256:" + diff_id)
env = cfg["config"]["Env"]
env = [("NASTOOL_AUTO_UPDATE=false" if e.startswith("NASTOOL_AUTO_UPDATE=") else e) for e in env]
cfg["config"]["Env"] = env
cfg["history"].append({
    "created": meta["created"],
    "created_by": "MOD ui: 极简苹果风主题 (apple.css + 模板/组件配色)",
    "comment": "apple-theme",
})
json.dump(cfg, open(os.path.join(STAGE, CFG), "w", encoding="utf-8"),
          ensure_ascii=False, separators=(",", ":"))

# ---------- 4. manifest ----------
manifest = json.load(open(os.path.join(LAYERS, "manifest.json"), encoding="utf-8"))
manifest[0]["RepoTags"] = ["syly948/nastools:2.9.1-apple"]
manifest[0]["Layers"].append(f"{new_id}/layer.tar")
json.dump(manifest, open(os.path.join(STAGE, "manifest.json"), "w", encoding="utf-8"),
          ensure_ascii=False, separators=(",", ":"))

# ---------- 5. 硬链接旧层，避免复制 1GB ----------
for d in OLD_DIRS:
    dst = os.path.join(STAGE, d)
    os.makedirs(dst, exist_ok=True)
    for f in os.listdir(os.path.join(LAYERS, d)):
        os.link(os.path.join(LAYERS, d, f), os.path.join(dst, f))

# repositories（旧格式兼容，指向最新层）
json.dump({"syly948/nastools": {"2.9.1-apple": new_id}},
          open(os.path.join(STAGE, "repositories"), "w", encoding="utf-8"),
          separators=(",", ":"))
print("stage ready:", STAGE)
