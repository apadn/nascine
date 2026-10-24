#!/usr/bin/env python3
"""按 release.json 出镜像：改镜像名 / 改版本号 / 改更新源，并输出可直接 docker load 的 tar。

只做三件事，全部围绕「发一个自己的镜像」：
  1. 用 baseTar 作为基础镜像，把 rootfs/nascine 与它自动 diff 出新增/修改/删除，
     打成新的一层（不需要手工维护改动清单）
  2. 改写 version.py 的版本号，改写 config.json 里的 Env / OCI Labels / created
  3. 改写 manifest.json 的 RepoTags 与 repositories，输出 <repository>-<version>.tar

后续修 bug 发版的完整流程：
    vim rootfs/nascine/<要改的文件>
    # 改 release.json 里的 version：2.9.1-r1 -> 2.9.1-r2
    python3 make_release.py
    docker load -i ../nascine-1.0.3.tar
    docker push <namespace>/nascine:1.0.3
    # NAS 上 docker compose pull && docker compose up -d

常用参数：
    --version 2.9.1-r2      覆盖 release.json 的版本号
    --namespace yourid      覆盖命名空间（Docker Hub 用户名）
    --repository xxx        覆盖仓库名
    --base ../xxx.tar       覆盖基础镜像
    --dry-run               只做 diff 与元数据计算，不落盘
"""
import argparse
import gzip
import hashlib
import io
import json
import os
import re
import shutil
import sys
import tarfile
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
IMAGE_ROOT = "nascine"   # 容器内代码目录（1.0.3 起由 /nas-tools 改名）
APP = os.path.join(HERE, "rootfs", IMAGE_ROOT)
WORK = None  # 每次运行在系统临时目录下创建，结束时删除
CFG_FILE = os.path.join(HERE, "release.json")

# 瘦身时从镜像里剔除的目录：源码中保留（便于对照与跑单测），但不打进镜像。
# 必须与 slim/prune.sh 的删除项保持一致，否则每次发版又会把它们加回来。
#   third_party/plexapi/tests 里有 18MB 的 video_stub.mp4 / audio_stub.mp3，只服务 plexapi 单测
IMAGE_EXCLUDE = (
    "third_party/plexapi/tests/",
)


def log(msg):
    print("[release] %s" % msg, flush=True)


def load_conf():
    with open(CFG_FILE, encoding="utf-8") as fh:
        return json.load(fh)


def save_conf(conf):
    with open(CFG_FILE, "w", encoding="utf-8") as fh:
        json.dump(conf, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def parse_version(version):
    """2.9.1-r2 -> ("2.9.1", "r2")"""
    match = re.match(r"^[vV]?(\d+(?:\.\d+)*)(?:[-_.]?([A-Za-z]+)(\d+))?$", version)
    if not match:
        sys.exit("版本号格式不对，应为 2.9.1 或 2.9.1-r1 形式：%s" % version)
    base = match.group(1)
    revision = ""
    if match.group(2):
        revision = "%s%s" % (match.group(2), match.group(3))
    return base, revision


def write_version_file(version):
    base, revision = parse_version(version)
    content = (
        "# 定制镜像版本号：v<上游版本>-<自定义后缀><修订号>\n"
        "# 由 make_release.py 依据 release.json 自动生成，不要手改\n"
        "APP_VERSION = 'v%s'\n"
        "\n"
        "# 上游基础版本（升级上游时同步修改 release.json）\n"
        "APP_VERSION_BASE = '%s'\n"
        "\n"
        "# 定制修订号\n"
        "APP_VERSION_REVISION = '%s'\n" % (version, base, revision or "")
    )
    with open(os.path.join(APP, "version.py"), "w", encoding="utf-8") as fh:
        fh.write(content)
    return "v" + version


# ---------------------------------------------------------------- 解包 / diff
def extract_outer(tar_path, dest):
    """解包镜像 tar 的外层结构：manifest.json / config.json / repositories / <layer>/"""
    with tarfile.open(tar_path) as tf:
        for member in tf.getmembers():
            name = member.name.lstrip("./").rstrip("/")
            if not name:
                continue
            target = os.path.join(dest, name)
            if member.isdir():
                os.makedirs(target, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            src = tf.extractfile(member)
            if src is None:
                continue
            with open(target, "wb") as fh:
                shutil.copyfileobj(src, fh)


def flatten_image(tar_path, dest):
    """把镜像的所有层按顺序叠成一个目录树（处理 .wh.xxx 白化文件）"""
    with tarfile.open(tar_path) as outer:
        manifest = json.load(outer.extractfile("manifest.json"))
        layer_paths = manifest[0]["Layers"]
        for layer_path in layer_paths:
            data = outer.extractfile(layer_path)
            with tarfile.open(fileobj=data) as layer:
                for member in layer.getmembers():
                    name = member.name.lstrip("./").rstrip("/")
                    if not name:
                        continue
                    # 只还原 nas-tools 目录，其余系统路径不需要参与 diff，
                    # 同时避免写穿层内的绝对符号链接
                    if name != IMAGE_ROOT and not name.startswith(IMAGE_ROOT + "/"):
                        continue
                    target = os.path.join(dest, name)
                    base = os.path.basename(name)
                    if base.startswith(".wh."):
                        victim = os.path.join(os.path.dirname(target), base[4:])
                        if os.path.isdir(victim):
                            shutil.rmtree(victim, ignore_errors=True)
                        elif os.path.exists(victim) or os.path.islink(victim):
                            os.remove(victim)
                        continue
                    if member.isdir():
                        os.makedirs(target, exist_ok=True)
                        continue
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    if member.issym():
                        if os.path.lexists(target):
                            os.remove(target)
                        os.symlink(member.linkname, target)
                        continue
                    if member.islnk():
                        src = os.path.join(dest, member.linkname)
                        if os.path.exists(src):
                            shutil.copy2(src, target)
                        continue
                    src = layer.extractfile(member)
                    if src is None:
                        continue
                    if os.path.islink(target):
                        os.remove(target)
                    with open(target, "wb") as fh:
                        shutil.copyfileobj(src, fh)
                    os.chmod(target, member.mode & 0o777)
    return manifest


def layer_diff_id(data):
    """层字节对应的 diff_id：docker save 出来的 OCI 层是 gzip 的，diff_ids 记的是解压后的摘要"""
    if data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)
    return "sha256:" + hashlib.sha256(data).hexdigest()


def tree_hashes(root):
    result = {}
    for dirpath, _, files in os.walk(root):
        for name in files:
            path = os.path.join(dirpath, name)
            if os.path.islink(path):
                result[os.path.relpath(path, root)] = "link:" + os.readlink(path)
                continue
            try:
                with open(path, "rb") as fh:
                    result[os.path.relpath(path, root)] = hashlib.sha256(fh.read()).hexdigest()
            except OSError:
                continue
    return result


def is_excluded(path):
    """是否属于瘦身剔除项（不进镜像）"""
    return any(path == x.rstrip("/") or path.startswith(x) for x in IMAGE_EXCLUDE)


def diff_tree(base_root, new_root):
    base = tree_hashes(base_root)
    new = tree_hashes(new_root)
    added = sorted(set(new) - set(base))
    changed = sorted(k for k in set(base) & set(new) if base[k] != new[k])
    deleted = sorted(set(base) - set(new))
    # 忽略本地编译产物
    dirty = (".pyc", ".pyo")
    added = [f for f in added if not f.endswith(dirty)]
    changed = [f for f in changed if not f.endswith(dirty)]
    deleted = [f for f in deleted if not f.endswith(dirty)]
    return added, changed, deleted


# ---------------------------------------------------------------- 打层
def build_layer(layer_dir, added, changed, deleted):
    layer_tar = os.path.join(layer_dir, "layer.tar")
    mtime = int(time.time())

    def dir_entry(name):
        info = tarfile.TarInfo(name)
        info.type = tarfile.DIRTYPE
        info.mode = 0o755
        info.uid = info.gid = 0
        info.uname = info.gname = "root"
        info.mtime = mtime
        return info

    def whiteout_entry(name):
        info = tarfile.TarInfo(name)
        info.size = 0
        info.mode = 0o644
        info.uid = info.gid = 0
        info.uname = info.gname = "root"
        info.mtime = mtime
        return info, io.BytesIO(b"")

    with tarfile.open(layer_tar, "w", format=tarfile.PAX_FORMAT) as tf:
        seen_dirs = set()

        def ensure_dirs(rel):
            parts = rel.split("/")
            for i in range(1, len(parts)):
                name = IMAGE_ROOT + "/" + "/".join(parts[:i]) + "/"
                if name not in seen_dirs:
                    seen_dirs.add(name)
                    tf.addfile(dir_entry(name))

        for rel in sorted(added + changed):
            src = os.path.join(APP, rel)
            ensure_dirs(rel)
            info = tf.gettarinfo(src, arcname=IMAGE_ROOT + "/" + rel)
            info.uid = info.gid = 0
            info.uname = info.gname = "root"
            info.mode = 0o755 if (info.mode & 0o100) else 0o644
            info.mtime = mtime
            with open(src, "rb") as fh:
                tf.addfile(info, fh)

        for rel in sorted(deleted):
            ensure_dirs(rel)
            if "/" in rel:
                parent, name = rel.rsplit("/", 1)
                wh = "%s/%s/.wh.%s" % (IMAGE_ROOT, parent, name)
            else:
                # 顶层文件（如 .gitmodules）没有父目录
                wh = "%s/.wh.%s" % (IMAGE_ROOT, rel)
            info, buf = whiteout_entry(wh)
            tf.addfile(info, buf)

    with open(layer_tar, "rb") as fh:
        data = fh.read()
    return layer_tar, hashlib.sha256(data).hexdigest(), len(data)


# ---------------------------------------------------------------- 元数据
def set_env(env_list, key, value):
    env_list = [e for e in env_list if e.split("=", 1)[0] != key]
    if value not in (None, ""):
        env_list.append("%s=%s" % (key, value))
    return env_list


def rewrite_config(cfg, repo, version, update, image_id, created):
    cfg["created"] = created
    config = cfg.get("config") or {}
    env = list(config.get("Env") or [])
    # 上游遗留的 NASTOOL_* 变量全部清除，统一改用 NASCINE_* 前缀；
    # REPO_URL / PYPI_MIRROR / ALPINE_MIRROR 只服务于已被删掉的 git 自动更新，一并清掉
    drop = ("NASTOOL_", "REPO_URL", "PYPI_MIRROR", "ALPINE_MIRROR")
    env = [e for e in env if not e.startswith(drop)]
    env = set_env(env, "NASCINE_CONFIG", "/config/config.yaml")
    env = set_env(env, "NASCINE_IMAGE_REPO", repo)
    env = set_env(env, "NASCINE_UPDATE_MODE", update.get("mode") or "docker")
    env = set_env(env, "NASCINE_UPDATE_API", update.get("api") or "")
    env = set_env(env, "NASCINE_UPDATE_URL", update.get("url") or "")
    env = set_env(env, "NASCINE_FLAVOR", "full")
    config["Env"] = env

    hub_url = ("https://hub.docker.com/r/%s/tags" % repo) if "/" in repo \
        else ("https://hub.docker.com/_/%s/tags" % repo)
    labels = dict(config.get("Labels") or {})
    labels.update({
        "org.opencontainers.image.title": repo.split("/")[-1],
        "org.opencontainers.image.version": version,
        "org.opencontainers.image.revision": image_id,
        "org.opencontainers.image.created": created,
        "org.opencontainers.image.source": "https://hub.docker.com/r/%s" % repo,
        "org.opencontainers.image.url": hub_url,
        "org.opencontainers.image.vendor": repo.split("/")[0] if "/" in repo else "",
        "org.opencontainers.image.description": update.get("description") or "",
    })
    # 丢弃上游残留的无关标签，避免镜像元数据里继续出现旧项目名
    for key in list(labels):
        if key.lower().startswith("org.opencontainers.image") and not labels[key]:
            labels.pop(key)
    config["Labels"] = labels

    # 保留原始 Dockerfile 生成的入口点，只改容器运行时配置
    if "container_config" in cfg and isinstance(cfg["container_config"], dict):
        cfg["container_config"]["Env"] = env
        cfg["container_config"]["Labels"] = labels
    cfg["config"] = config
    return cfg


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version")
    parser.add_argument("--namespace")
    parser.add_argument("--repository")
    parser.add_argument("--base")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    conf = load_conf()
    version = args.version or conf["version"]
    namespace = args.namespace if args.namespace is not None else conf.get("namespace", "")
    repository = args.repository or conf["repository"]
    base_tar = os.path.abspath(args.base or os.path.join(HERE, conf["baseTar"]))
    update = dict(conf.get("update") or {})
    if conf.get("description"):
        update["description"] = conf["description"]

    if not os.path.isfile(base_tar):
        sys.exit("基础镜像不存在：%s" % base_tar)

    repo = "%s/%s" % (namespace, repository) if namespace else repository
    if namespace in ("", "CHANGE_ME"):
        log("警告：release.json 里的 namespace 还是占位值，镜像名会变成 %s，推送到 Docker Hub 前必须改成你的用户名" % repo)

    log("目标镜像 %s:%s" % (repo, version))

    global WORK
    # 用系统临时目录，避免在项目里留下几个 G 的中间文件；
    # 某些受限环境（沙箱禁止删除）拿不到系统临时目录时，退回到项目内的 .release-work
    try:
        WORK = tempfile.mkdtemp(prefix="nascine-release-")
    except OSError:
        WORK = os.path.join(HERE, ".release-work-%d" % int(time.time()))
        os.makedirs(WORK, exist_ok=True)
        log("系统临时目录不可用，改用项目内工作目录")
    log("工作目录 %s" % WORK)

    # 1) 版本号写回源码
    app_version = write_version_file(version)
    log("version.py -> APP_VERSION = %s" % app_version)

    # 2) 解包基础镜像，算出与当前源码树的差异
    outer_dir = os.path.join(WORK, "outer")
    os.makedirs(outer_dir)
    log("解包基础镜像（%s）..." % os.path.basename(base_tar))
    extract_outer(base_tar, outer_dir)
    with open(os.path.join(outer_dir, "manifest.json"), encoding="utf-8") as fh:
        manifest = json.load(fh)

    base_fs = os.path.join(WORK, "base_fs")
    os.makedirs(base_fs)
    flatten_image(base_tar, base_fs)

    base_app = os.path.join(base_fs, IMAGE_ROOT)
    if not os.path.isdir(base_app):
        sys.exit("基础镜像里没有 %s 目录，镜像结构不符" % IMAGE_ROOT)

    added, changed, deleted = diff_tree(base_app, APP)
    # 瘦身剔除项即便源码有、基础镜像没有，也不加进镜像
    added = [f for f in added if not is_excluded(f)]
    changed = [f for f in changed if not is_excluded(f)]
    log("新增 %d 个文件，修改 %d 个，删除 %d 个" % (len(added), len(changed), len(deleted)))
    for name in added[:30]:
        log("  + %s" % name)
    for name in changed[:30]:
        log("  ~ %s" % name)
    for name in deleted[:30]:
        log("  - %s" % name)
    if not (added or changed or deleted):
        log("源码与基础镜像完全一致，仍会更新版本号与元数据")

    if args.dry_run:
        log("dry-run 结束，未落盘")
        return

    # 3) 打新层
    image_id = hashlib.sha256(
        ("%s|%s|%.6f" % (repo, version, time.time())).encode()).hexdigest()
    layer_dir = os.path.join(WORK, image_id)
    os.makedirs(layer_dir)
    layer_tar, diff_id, size = build_layer(layer_dir, added, changed, deleted)
    log("新层 %s（%.1f KB）" % (image_id[:12], size / 1024))

    created = time.strftime("%Y-%m-%dT%H:%M:%S+08:00")

    # 4) 层元数据
    top_id = manifest[0]["Layers"][-1].split("/")[0]
    top_meta_path = os.path.join(outer_dir, top_id, "json")
    meta = {}
    if os.path.isfile(top_meta_path):
        with open(top_meta_path, encoding="utf-8") as fh:
            meta = json.load(fh)
    meta.update({"id": image_id, "parent": top_id, "created": created})
    with open(os.path.join(layer_dir, "json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(layer_dir, "VERSION"), "w") as fh:
        fh.write("1.0")

    # 5) config.json：Env / Labels / diff_ids / history
    old_cfg_name = manifest[0]["Config"]
    with open(os.path.join(outer_dir, old_cfg_name), encoding="utf-8") as fh:
        cfg = json.load(fh)
    cfg["rootfs"]["diff_ids"].append("sha256:" + diff_id)
    cfg["history"].append({
        "created": created,
        "created_by": "release %s:%s" % (repo, version),
        "comment": "custom-build",
    })
    cfg = rewrite_config(cfg, repo, version, update, image_id, created)

    cfg_bytes = json.dumps(cfg, ensure_ascii=False, separators=(",", ":")).encode()
    new_cfg_name = hashlib.sha256(cfg_bytes).hexdigest() + ".json"
    with open(os.path.join(WORK, new_cfg_name), "wb") as fh:
        fh.write(cfg_bytes)

    # 6) manifest / repositories
    manifest[0]["Config"] = new_cfg_name
    manifest[0]["RepoTags"] = ["%s:%s" % (repo, version), "%s:latest" % repo]
    manifest[0]["Layers"].append("%s/layer.tar" % image_id)
    with open(os.path.join(WORK, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(WORK, "repositories"), "w", encoding="utf-8") as fh:
        json.dump({repo: {version: image_id, "latest": image_id}}, fh, separators=(",", ":"))

    # 旧层目录直接从外层解包目录引用，新层用自己的目录
    layer_dirs = [l.split("/")[0] for l in manifest[0]["Layers"][:-1]]
    layer_src = {name: os.path.join(outer_dir, name) for name in layer_dirs}
    layer_src[image_id] = layer_dir

    # 7) 打包
    out_name = "%s-%s.tar" % (repository, version)
    out_path = os.path.join(os.path.dirname(HERE), out_name)
    with tarfile.open(out_path, "w", format=tarfile.PAX_FORMAT) as tf:
        for name in ("manifest.json", new_cfg_name, "repositories"):
            tf.add(os.path.join(WORK, name), arcname=name)
        for name in layer_dirs + [image_id]:
            tf.add(layer_src[name], arcname=name)
    log("已输出 %s（%.1f MB）" % (out_path, os.path.getsize(out_path) / 1024 / 1024))

    # 8) 自检
    with tarfile.open(out_path) as tf:
        man = json.load(tf.extractfile("manifest.json"))
        new_cfg = json.load(tf.extractfile(man[0]["Config"]))
        ok = True
        for layer_path, expect in zip(man[0]["Layers"], new_cfg["rootfs"]["diff_ids"]):
            got = layer_diff_id(tf.extractfile(layer_path).read())
            if got != expect:
                ok = False
                log("自检失败：%s 期望 %s 实际 %s" % (layer_path, expect[:19], got[:19]))
        log("自检：层数 %d，diff_ids 全部匹配 %s，RepoTags %s" % (
            len(man[0]["Layers"]), ok, man[0]["RepoTags"]))
        env = new_cfg["config"]["Env"]
        log("自检：%s" % " ".join(e for e in env if e.startswith(("NASCINE_", "PUID", "PGID"))))
        if not ok:
            sys.exit("镜像校验失败，请检查")

    # 9) 回写 release.json（下次发版以本次镜像为基础，版本号保持同步）
    conf["version"] = version
    conf["namespace"] = namespace
    if os.path.abspath(base_tar) != os.path.abspath(out_path):
        conf["baseTar"] = os.path.relpath(out_path, HERE)
    save_conf(conf)

    shutil.rmtree(WORK, ignore_errors=True)

    print("")
    print("下一步：")
    print("  docker load -i %s" % out_path)
    print("  docker push %s:%s" % (repo, version))
    print("  docker push %s:latest" % repo)
    print("")
    print("NAS 上更新：")
    print("  docker compose pull && docker compose up -d")
    print("")
    print("下次修 bug：改完代码把 release.json 的 version 改成 %s，再跑一次本脚本" % bump(version))


def bump(version):
    """下一版版本号：1.0.0 -> 1.0.1；带 -rN 的仍按 r 递增（兼容老命名）"""
    base, revision = parse_version(version)
    match = re.match(r"^([A-Za-z]+)(\d+)$", revision or "")
    if match:
        return "%s-%s%d" % (base, match.group(1), int(match.group(2)) + 1)
    parts = base.split(".")
    parts[-1] = str(int(parts[-1]) + 1)
    return ".".join(parts)


if __name__ == "__main__":
    main()
