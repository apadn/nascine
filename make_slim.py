#!/usr/bin/env python3
"""压缩 nascine 镜像体积：裁剪无用组件 + 扁平化成单层，功能和启动方式完全不变。

为什么不能只用 make_release.py 删文件：
    Docker 镜像体积 = 各层之和。在新增层里 rm 只是写一个 whiteout 标记，
    原来那 248 MB 的 chromium 仍然留在基础层里，拉取体积不会有任何变化。
    必须把文件系统 export 出来重新 import 成**单层**镜像，删掉的字节才真正消失。

流程（全部自动完成）：
    1. 生成临时 Dockerfile：FROM 源镜像 + 执行 slim/prune.sh
    2. docker build 出中间镜像
    3. docker create + docker export 拿到扁平的根文件系统
    4. docker import 并逐条还原源镜像的 Config（ENV / ENTRYPOINT / WORKDIR /
       VOLUME / EXPOSE / USER / STOPSIGNAL / LABELS）
    5. docker save 输出 <repository>-<version>.tar，可直接 docker load

用法：
    python3 make_slim.py                              # release.json 的 version 递增为输出标签
    python3 make_slim.py --version 1.0.6              # 指定输出标签
    python3 make_slim.py --source xdxy/nascine:1.0.5 --target xdxy/nascine:1.0.6
    python3 make_slim.py --dry-run                    # 只打印将要执行的动作
    python3 make_slim.py --keep                       # 保留中间镜像/临时 tar，便于排查
"""
import argparse
import json
import os
import shutil
import subprocess
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PRUNE_SH = os.path.join(HERE, "slim", "prune.sh")
RELEASE_JSON = os.path.join(HERE, "release.json")


def run(cmd, **kwargs):
    """执行命令，失败时打印完整命令便于复现"""
    if kwargs.get("capture"):
        kwargs.pop("capture")
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if proc.returncode != 0:
            print(proc.stdout)
            raise SystemExit("命令失败：%s" % " ".join(cmd))
        return proc.stdout.strip()
    proc = subprocess.run(cmd)
    if proc.returncode != 0:
        raise SystemExit("命令失败：%s" % " ".join(cmd))
    return ""


def human(size):
    size = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return "%.1f %s" % (size, unit)
        size /= 1024


def image_config(image):
    """读取镜像 Config，用于 import 时还原"""
    raw = run(["docker", "image", "inspect", image, "--format", "{{json .Config}}"], capture=True)
    cfg = json.loads(raw)
    size = int(run(["docker", "image", "inspect", image, "--format", "{{.Size}}"], capture=True))
    return cfg, size


def quote_value(value):
    """--change 的值里含空格时必须加引号，否则 docker 解析 k=v 会报
    「can't find = in ...」（典型受害者是 PS1 和带空格的中文 description）"""
    if " " in value or '"' in value:
        return '"%s"' % value.replace('"', '\\"')
    return value


def change_args(cfg, labels_over):
    """由源镜像 Config 生成 docker import --change 参数"""
    changes = []
    for env in cfg.get("Env") or []:
        key, _, value = env.partition("=")
        changes.append("ENV %s=%s" % (key, quote_value(value)))
    if cfg.get("Entrypoint"):
        changes.append("ENTRYPOINT %s" % json.dumps(cfg["Entrypoint"]))
    if cfg.get("Cmd"):
        changes.append("CMD %s" % json.dumps(cfg["Cmd"]))
    if cfg.get("WorkingDir"):
        changes.append("WORKDIR %s" % cfg["WorkingDir"])
    if cfg.get("User"):
        changes.append("USER %s" % cfg["User"])
    if cfg.get("StopSignal"):
        changes.append("STOPSIGNAL %s" % cfg["StopSignal"])
    for port in (cfg.get("ExposedPorts") or {}):
        changes.append("EXPOSE %s" % port)
    for vol in (cfg.get("Volumes") or {}):
        changes.append("VOLUME %s" % vol)
    labels = dict(cfg.get("Labels") or {})
    labels.update(labels_over)
    for key, value in labels.items():
        if value is None:
            continue
        changes.append("LABEL %s=%s" % (key, quote_value(str(value))))
    return changes


def main():
    parser = argparse.ArgumentParser(description="裁剪并扁平化 nascine 镜像")
    parser.add_argument("--source", default=None, help="源镜像，默认按 release.json 推断")
    parser.add_argument("--target", default=None, help="目标镜像标签")
    parser.add_argument("--version", default=None, help="目标版本号，默认取 release.json")
    parser.add_argument("--out", default=None, help="输出的 tar 路径，默认 ../<repository>-<version>.tar")
    parser.add_argument("--prune", default=PRUNE_SH, help="裁剪脚本路径")
    parser.add_argument("--base-tag", default=None, help="源镜像标签，默认 latest")
    parser.add_argument("--dry-run", action="store_true", help="只打印动作")
    parser.add_argument("--keep", action="store_true", help="保留中间产物")
    args = parser.parse_args()

    with open(RELEASE_JSON, "r", encoding="utf-8") as f:
        release = json.load(f)
    namespace = release.get("namespace", "xdxy")
    repository = release.get("repository", "nascine")
    version = args.version or release.get("version")
    if not version:
        raise SystemExit("无法确定版本号，请用 --version 指定")

    source = args.source or "%s/%s:%s" % (namespace, repository, args.base_tag or "latest")
    target = args.target or "%s/%s:%s" % (namespace, repository, version)
    out_tar = args.out or os.path.abspath(os.path.join(HERE, "..", "%s-%s.tar" % (repository, version)))
    tmp_tag = "nascine-slim-build:%s" % version
    tmp_container = "nascine-slim-%d" % int(time.time())

    if not os.path.isfile(args.prune):
        raise SystemExit("裁剪脚本不存在：%s" % args.prune)

    cfg, src_size = image_config(source)
    changes = change_args(cfg, {
        "org.opencontainers.image.version": version,
        "org.opencontainers.image.created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "org.opencontainers.image.description": release.get("description") or None,
    })

    print("=" * 72)
    print("源镜像  : %s（%s）" % (source, human(src_size)))
    print("目标镜像: %s" % target)
    print("输出 tar: %s" % out_tar)
    print("=" * 72)

    if args.dry_run:
        print("\n--- 临时 Dockerfile ---")
        print("FROM %s" % source)
        print("COPY %s /tmp/prune.sh" % os.path.basename(args.prune))
        print("RUN sh /tmp/prune.sh && rm -f /tmp/prune.sh")
        print("\n--- docker import --change ---")
        for item in changes:
            print("  -c %r" % item)
        return

    workdir = tempfile.mkdtemp(prefix="nascine-slim-")
    export_tar = os.path.join(workdir, "rootfs.tar")
    try:
        # 1) 临时 Dockerfile：应用裁剪脚本 + 改写版本号
        shutil.copy2(args.prune, os.path.join(workdir, "prune.sh"))
        dockerfile = os.path.join(workdir, "Dockerfile")
        base_version = version.split("-r")[0]
        revision = version[len(base_version):].lstrip("-r").strip("-")
        with open(dockerfile, "w", encoding="utf-8") as f:
            f.write("FROM %s\n" % source)
            f.write("COPY prune.sh /tmp/prune.sh\n")
            f.write("RUN sh /tmp/prune.sh && rm -f /tmp/prune.sh\n")
            # 版本号规则与 make_release.py 保持一致，避免镜像标签是 1.0.6、
            # 而界面里还显示上一个版本
            f.write('RUN sed -i "s|^APP_VERSION = .*|APP_VERSION = \'v%s\'|" /nascine/version.py\n'
                    % version)
            f.write('RUN sed -i "s|^APP_VERSION_BASE = .*|APP_VERSION_BASE = \'%s\'|" '
                    '/nascine/version.py\n' % base_version)
            f.write('RUN sed -i "s|^APP_VERSION_REVISION = .*|APP_VERSION_REVISION = \'%s\'|" '
                    '/nascine/version.py\n' % revision)
            f.write("RUN grep -E '^APP_VERSION' /nascine/version.py\n")

        print("\n[1/5] 构建裁剪层 ...")
        run(["docker", "build", "--platform", "linux/amd64",
             "-f", dockerfile, "-t", tmp_tag, workdir])
        # 2) 导出扁平的文件系统（create 而不是 run，避免 /config 变成匿名卷丢内容）
        print("[2/5] 导出根文件系统 ...")
        run(["docker", "rm", "-f", tmp_container])
        run(["docker", "create", "--name", tmp_container, tmp_tag])
        run(["docker", "export", "-o", export_tar, tmp_container])
        print("      导出大小：%s" % human(os.path.getsize(export_tar)))

        # 3) 重新导入成单层镜像，并还原元数据
        print("[3/5] 重新导入为单层镜像 ...")
        run(["docker", "rmi", "-f", target])
        cmd = ["docker", "import", "--platform", "linux/amd64"]
        for item in changes:
            cmd += ["-c", item]
        cmd += [export_tar, target]
        run(cmd)

        # 4) 输出可 load 的 tar
        print("[4/5] 导出镜像 tar ...")
        run(["docker", "save", "-o", out_tar, target])
        print("      tar 大小：%s" % human(os.path.getsize(out_tar)))

        # 5) 汇总
        _, dst_size = image_config(target)
        print("[5/5] 完成")
        print("-" * 72)
        print("镜像体积：%s -> %s（减少 %s，%.0f%%）" % (
            human(src_size), human(dst_size),
            human(src_size - dst_size), (1 - dst_size / float(src_size)) * 100))
        print("产物     ：%s" % out_tar)
        print("-" * 72)
        print("下一步：")
        print("    docker load -i %s" % out_tar)
        print("    docker run -d --name nascine -p 3000:3000 -v /path/config:/config "
              "-v /path/downloads:/downloads -v /path/media:/media %s" % target)
    finally:
        if args.keep:
            print("中间产物保留在：%s（镜像 %s）" % (workdir, tmp_tag))
        else:
            for cleanup in (["docker", "rm", "-f", tmp_container], ["docker", "rmi", "-f", tmp_tag]):
                subprocess.run(cleanup, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    main()
