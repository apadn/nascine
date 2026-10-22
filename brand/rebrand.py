#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 NAS-Tools 品牌文本统一替换为 nascine。

保留项（不能被替换）：
  /nas-tools            容器内代码路径（文件系统路径，改动会破坏镜像层）
  nastool.cn            上游作者提供的公共代理/OCR/CookieCloud 服务域名
  ONLYNASTOOL           数据库列名（已有库结构，改名需迁移）

用法：python rebrand.py <root> [--dry]
"""

import os
import re
import sys

SKIP_DIRS = {".git", "__pycache__", "third_party", "node_modules"}
SKIP_FILES = {"sites.dat", "package-lock.json"}
SKIP_EXT = {".pyc", ".pyo", ".png", ".jpg", ".jpeg", ".ico", ".gif",
            ".ttf", ".woff", ".woff2", ".eot", ".zip", ".tar", ".gz", ".db"}

# 由人工逐文件重写的文件，不参与批量替换
MANUAL = {
    "docker/entrypoint.sh", "docker/compose.yml", "docker/readme.md",
    "README.md", "docker/Dockerfile", "docker/Dockerfile.lite",
    "docker/Dockerfile.beta", "web/templates/setting/directorysync.html",
}

P = {
    "/nas-tools": "\x01P1\x01",
    "nastool.cn": "\x01P2\x01",
    "ONLYNASTOOL": "\x01P3\x01",
    "onlynastool": "\x01P4\x01",
}

# 顺序敏感：先整体大写（环境变量 / 标签），再混合大小写
RULES = [
    ("NASTOOL", "NASCINE"),
    ("NAS-Tools", "nascine"),
    ("NAS-Tool", "nascine"),
    ("NAStool", "nascine"),
    ("NASTool", "nascine"),
    ("nastools", "nascine"),
    ("nastool", "nascine"),
    ("nas-tools", "nascine"),
]


def protect(text):
    for k, v in P.items():
        text = text.replace(k, v)
    return text


def restore(text):
    for k, v in P.items():
        text = text.replace(v, k)
    return text


def rebrand(text):
    out = protect(text)
    for a, b in RULES:
        out = out.replace(a, b)
    return restore(out)


def main():
    root = os.path.abspath(sys.argv[1])
    dry = "--dry" in sys.argv
    total = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            if rel in MANUAL or name in SKIP_FILES:
                continue
            if os.path.splitext(name)[1].lower() in SKIP_EXT:
                continue
            if os.path.islink(path):
                continue
            try:
                raw = open(path, "rb").read()
                text = raw.decode("utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if not re.search(r"(?i)nas[-_ ]?tools?", text):
                continue
            new = rebrand(text)
            if new == text:
                continue
            hits = len(re.findall(r"(?i)nas[-_ ]?tools?", text)) - \
                len(re.findall(r"(?i)nas[-_ ]?tools?", new))
            print("%3d  %s" % (hits, rel))
            total += hits
            if not dry:
                open(path, "w", encoding="utf-8").write(new)
    print("---- 共替换 %d 处（%s）" % (total, "dry-run" if dry else "已写入"))


if __name__ == "__main__":
    main()
