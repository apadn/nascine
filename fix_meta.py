#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只改镜像元数据（Config.Env / manifest），不动任何层字节。

用途：沙箱禁止删除文件时，无法重跑 make_release（它要靠 whiteout 还原基础镜像），
用本脚本直接改写 tar 里的 config json 与 manifest，层的 sha256 / diff_ids 完全不变。
"""

import hashlib
import io
import json
import os
import sys
import tarfile

DROP_PREFIX = ("NASTOOL_", "REPO_URL", "PYPI_MIRROR", "ALPINE_MIRROR")


def main():
    src = sys.argv[1]
    dst = src + ".new"

    with tarfile.open(src) as tf:
        names = tf.getnames()
        manifest = json.load(tf.extractfile("manifest.json"))
        old_cfg_name = manifest[0]["Config"]
        cfg = json.load(tf.extractfile(old_cfg_name))

    env = cfg["config"]["Env"]
    kept = [e for e in env if not e.startswith(DROP_PREFIX)]
    dropped = [e for e in env if e.startswith(DROP_PREFIX)]
    cfg["config"]["Env"] = kept
    if "container_config" in cfg:
        cfg["container_config"]["Env"] = kept

    cfg_bytes = json.dumps(cfg, ensure_ascii=False, separators=(",", ":")).encode()
    new_cfg_name = hashlib.sha256(cfg_bytes).hexdigest() + ".json"
    manifest[0]["Config"] = new_cfg_name
    man_bytes = json.dumps(manifest, ensure_ascii=False, separators=(",", ":")).encode()

    print("移除环境变量：", ", ".join(e.split("=")[0] for e in dropped) or "无")
    print("config: %s -> %s" % (old_cfg_name[:16], new_cfg_name[:16]))

    with tarfile.open(src) as tf, tarfile.open(dst, "w", format=tarfile.PAX_FORMAT) as out:
        for m in tf.getmembers():
            if m.name == old_cfg_name:
                continue  # 旧 config 换成新名字的条目（下面追加）
            if m.name == "manifest.json":
                info = tarfile.TarInfo("manifest.json")
                info.size = len(man_bytes)
                info.mode = 0o644
                info.mtime = m.mtime
                out.addfile(info, io.BytesIO(man_bytes))
                continue
            f = tf.extractfile(m) if m.isfile() else None
            out.addfile(m, f)

        info = tarfile.TarInfo(new_cfg_name)
        info.size = len(cfg_bytes)
        info.mode = 0o644
        out.addfile(info, io.BytesIO(cfg_bytes))

    os.replace(dst, src)
    print("已写回", src, "%.1f MB" % (os.path.getsize(src) / 1024 / 1024))


if __name__ == "__main__":
    main()
