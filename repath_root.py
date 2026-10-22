#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把已有镜像里的容器内代码目录 /nas-tools 整体改名为 /nascine。

做法（等于重建基础镜像，但不动任何层的内容语义）：
  1. 逐层流式读取，把条目路径前缀 nas-tools/ 换成 nascine/，
     同时处理 symbolic link 的 linkname；
  2. 把 /usr/lib/python3.10/site-packages/nas-tools.pth 改名为 nascine.pth
     并重写其中的 sys.path 行；
  3. 追加一个只有几十字节的清理层，删掉上游遗留的 /root/.gitconfig
     （里面记着 /nas-tools 路径，且本镜像已不做任何 git 操作）；
  4. 重写 config：WORKDIR / ENTRYPOINT / WorkingDir 指到 /nascine，
     顺手清掉三个已无代码读取的死变量；
  5. 重算每层未压缩 tar 的 sha256 写回 rootfs.diff_ids，并按新 sha 命名层目录。

用法：
    python repath_root.py ../../nascine-1.0.2.tar ../../nascine-1.0.3-base.tar
"""
import copy
import hashlib
import io
import json
import os
import sys
import tarfile
import time

OLD = "nas-tools"
NEW = "nascine"
PTH_OLD = "usr/lib/python3.10/site-packages/nas-tools.pth"
PTH_NEW = "usr/lib/python3.10/site-packages/nascine.pth"
DEAD_ENV = ("REPO_URL", "PYPI_MIRROR", "ALPINE_MIRROR")


def log(msg):
    print(msg, flush=True)


def rename(name):
    """把路径前缀 nas-tools 换成 nascine"""
    if name == OLD or name == OLD + "/":
        return NEW + name[len(OLD):]
    if name.startswith(OLD + "/"):
        return NEW + name[len(OLD):]
    return name


def rewrite_bytes(name, data):
    """个别文件内容里也写死了 /nas-tools"""
    if name.endswith(".pth"):
        text = data.decode("utf-8")
        if "/nas-tools" in text:
            return text.replace("/nas-tools", "/nascine").encode("utf-8")
    return data


def rebuild_layer2(src, dst_path, tag):
    """重写一层，返回 (sha256hex, 新增/改动条目数)"""
    changed = 0
    with open(dst_path, "wb") as raw, \
            tarfile.open(fileobj=src, mode="r|*") as inner, \
            tarfile.open(fileobj=raw, mode="w", format=tarfile.PAX_FORMAT) as out:
        for m in inner:
            new_name = rename(m.name)
            if m.name == PTH_OLD:
                new_name = PTH_NEW
            if new_name != m.name:
                changed += 1
            ti = copy.copy(m)
            ti.name = new_name
            if ti.linkname:
                ti.linkname = rename(ti.linkname)
            # 长路径条目在 PAX 扩展头里另存了一份原始 path/linkpath，
            # 不清掉会把改好的名字又覆盖回去
            if ti.pax_headers:
                ti.pax_headers = {k: v for k, v in ti.pax_headers.items()
                                  if k not in ("path", "linkpath")}
            if m.isreg() and (m.size or 0) > 0:
                data = inner.extractfile(m).read()
                new_data = rewrite_bytes(m.name, data)
                if new_data is not data:
                    changed += 1
                ti.size = len(new_data)
                out.addfile(ti, io.BytesIO(new_data))
            else:
                out.addfile(ti)
    h = hashlib.sha256()
    with open(dst_path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    log("    %s 改动条目 %d，未压缩 %.1f MB"
        % (tag, changed, os.path.getsize(dst_path) / 1048576.0))
    return h.hexdigest(), changed


def build_cleanup_layer(path):
    """追加一层：删掉 /root/.gitconfig"""
    with open(path, "wb") as raw, \
            tarfile.open(fileobj=raw, mode="w", format=tarfile.PAX_FORMAT) as out:
        for name in ("root/.wh..gitconfig", ".wh.nas-tools"):
            ti = tarfile.TarInfo(name)
            ti.size = 0
            ti.mode = 0o644
            ti.mtime = int(time.time())
            out.addfile(ti)
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    src_path, dst_path = sys.argv[1], sys.argv[2]
    work = os.path.join(os.path.dirname(os.path.abspath(dst_path)), ".repath-work")
    os.makedirs(work, exist_ok=True)

    t = tarfile.open(src_path)
    man = json.load(t.extractfile("manifest.json"))
    cfg_name = man[0]["Config"]
    cfg = json.load(t.extractfile(cfg_name))
    layers = list(man[0]["Layers"])
    log("输入 %s —— %d 层" % (src_path, len(layers)))

    new_layers, new_diff_ids = [], []
    for i, lp in enumerate(layers):
        src = t.extractfile(lp)
        # 先探测这一层里有没有 nas-tools 前缀的条目
        probe = t.extractfile(lp)
        has_old = False
        with tarfile.open(fileobj=probe, mode="r|*") as inner:
            for m in inner:
                if m.name == OLD or m.name.startswith(OLD + "/") or m.name == PTH_OLD:
                    has_old = True
                    break
        if not has_old:
            log("  L%-2d 原样保留 (%.1f MB)" % (i, t.getmember(lp).size / 1048576.0))
            new_layers.append(lp)
            new_diff_ids.append(cfg["rootfs"]["diff_ids"][i])
            continue
        tmp = os.path.join(work, "L%d.tar" % i)
        sha, _ = rebuild_layer2(src, tmp, "L%d" % i)
        new_layers.append((sha, tmp, i))
        new_diff_ids.append("sha256:" + sha)

    # 清理层
    cleanup_tar = os.path.join(work, "cleanup.tar")
    cleanup_sha = build_cleanup_layer(cleanup_tar)
    new_layers.append((cleanup_sha, cleanup_tar, len(layers)))
    new_diff_ids.append("sha256:" + cleanup_sha)
    log("  追加清理层（删除 /root/.gitconfig）")

    # 元数据
    env = [e for e in (cfg["config"].get("Env") or [])
           if e.split("=", 1)[0] not in DEAD_ENV]
    env = [("WORKDIR=/nascine" if e.startswith("WORKDIR=") else e) for e in env]
    if not any(e.startswith("WORKDIR=") for e in env):
        env.append("WORKDIR=/nascine")
    cfg["config"]["Env"] = env
    cfg["config"]["WorkingDir"] = "/nascine"
    if cfg["config"].get("Entrypoint"):
        cfg["config"]["Entrypoint"] = [
            p.replace("/nas-tools", "/nascine") for p in cfg["config"]["Entrypoint"]]
    if cfg["config"].get("Cmd"):
        cfg["config"]["Cmd"] = [
            p.replace("/nas-tools", "/nascine") for p in cfg["config"]["Cmd"]]
    cfg["rootfs"]["diff_ids"] = new_diff_ids
    log("  元数据：WORKDIR=%s ENTRYPOINT=%s"
        % (cfg["config"]["WorkingDir"], cfg["config"]["Entrypoint"]))

    # 新层目录名 = 新 sha；未改动的层沿用原目录名
    layer_entries = []
    for item in new_layers:
        if isinstance(item, tuple):
            sha, tmp, idx = item
            layer_entries.append((sha, tmp))
        else:
            layer_entries.append((None, item))

    cfg_bytes = json.dumps(cfg, ensure_ascii=False).encode("utf-8")
    cfg_sha = hashlib.sha256(cfg_bytes).hexdigest()
    cfg_new_name = cfg_sha + ".json"

    log("写出 %s ..." % dst_path)
    with tarfile.open(dst_path, "w") as out:
        def add_bytes(name, data):
            ti = tarfile.TarInfo(name)
            ti.size = len(data)
            ti.mtime = int(os.path.getmtime(src_path))
            out.addfile(ti, io.BytesIO(data))

        add_bytes(cfg_new_name, cfg_bytes)

        for sha, ref in layer_entries:
            if sha:
                name = sha + "/layer.tar"
                ti = tarfile.TarInfo(name)
                ti.size = os.path.getsize(ref)
                ti.mtime = int(os.path.getmtime(src_path))
                with open(ref, "rb") as f:
                    out.addfile(ti, f)
                log("  + %s (重写)" % name[:16])
            else:
                f = t.extractfile(ref)
                ti = tarfile.TarInfo(ref)
                ti.size = t.getmember(ref).size
                ti.mtime = int(os.path.getmtime(src_path))
                out.addfile(ti, f)
                log("  + %s (原样)" % ref[:16])

        man[0]["RepoTags"] = [sys.argv[3] if len(sys.argv) > 3
                              else man[0]["RepoTags"][0] + "-base"]
        man[0]["Config"] = cfg_new_name
        man[0]["Layers"] = [sha + "/layer.tar" if sha else ref
                            for sha, ref in layer_entries]
        add_bytes("manifest.json",
                  json.dumps(man, ensure_ascii=False).encode("utf-8"))

    log("完成：%.1f MB" % (os.path.getsize(dst_path) / 1048576.0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
