# nascine

![Docker Pulls](https://img.shields.io/docker/pulls/xdxy/nascine)
![Image Version](https://img.shields.io/docker/v/xdxy/nascine/latest?label=image)
![License: AGPL v3](https://img.shields.io/badge/license-AGPL--3.0-blue.svg)
![Platform](https://img.shields.io/badge/platform-linux%2Famd64-lightgrey)

极简 · 苹果风的个人影音库中枢：**下载 → 整理 → 刮削**，一个容器跑完。

下载器里的文件落地后，nascine 会自动识别剧名 / 季集、按 TMDB 元数据重命名、刮削封面与简介，并按「电影 / 剧集 / 动漫」归档到媒体库目录。全程在 Web 界面上配置，不需要改配置文件。

## 这是什么

nascine 是 [nas-tools](https://github.com/jxxghp/nas-tools) 的精简定制版：保留媒体库、下载管理、目录同步、服务与系统设置，去掉 PT 站点、探索、资源搜索、订阅、豆瓣同步等模块，转移方式只保留「复制」和「移动」，不内置任何第三方代理、OCR、CookieCloud 服务。UI 整体重做成 iOS / macOS 风格的浅色主题。

它只做一件事：**把下载好的文件整理进媒体库**。鉴权、下载、播放交给 qBittorrent / Transmission / Emby / Jellyfin 这些专业工具。

## 功能范围

| 保留                                            | 已移除                            |
| --------------------------------------------- | ------------------------------ |
| 媒体库（电影 / 剧集 / 动漫）与刮削                          | PT 站点、做种、刷流                    |
| qBittorrent / Transmission / Aria2 / 115 等下载器 | 资源搜索、站点索引                      |
| 目录同步（监控目录自动识别改名转移）                            | 订阅、RSS 自动下载                    |
| 消息通知、自定义识别词、过滤规则                              | 豆瓣同步、媒体整理（硬链接整理）               |
| 服务控制、系统设置、版本更新提示                              | 第三方代理 / OCR / CookieCloud 内置服务 |

## 快速开始

### docker compose（推荐）

```yaml
services:
  nascine:
    image: xdxy/nascine:latest
    container_name: nascine
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - PUID=99
      - PGID=100
      - UMASK=002
      - TZ=Asia/Shanghai
    volumes:
      - /path/to/config:/config      # 配置与数据库
      - /path/to/downloads:/downloads # 下载器输出目录
      - /path/to/media:/media         # 媒体库目录
```

```bash
docker compose up -d
```

### docker run

```bash
docker run -d \
  --name nascine --restart unless-stopped \
  -p 3000:3000 \
  -v /path/to/config:/config \
  -v /path/to/downloads:/downloads \
  -v /path/to/media:/media \
  -e PUID=99 -e PGID=100 -e UMASK=002 -e TZ=Asia/Shanghai \
  xdxy/nascine:latest
```

启动后访问 `http://<ip>:3000`，默认账号 `admin` / 密码 `password`，**登录后请立即修改**。

### 三个目录

| 容器内路径        | 用途               | 说明                               |
| ------------ | ---------------- | -------------------------------- |
| `/config`    | 配置、SQLite 数据库、日志 | 必须持久化，否则重建容器后配置全丢                |
| `/downloads` | 下载器的输出目录         | 与下载器指向同一个宿主机目录，nascine 才能监控到文件   |
| `/media`     | 媒体库根目录           | 刮削后的文件归档到这里，供 Emby / Jellyfin 扫描 |

`PUID` / `PGID` 决定容器内进程身份，请与宿主机上 `/media` 目录的属主保持一致（群晖、Unraid 通常是 `99:100`），否则会出现「移动失败，错误码 -1」。

## 目录结构

```
.
├── rootfs/nascine/          容器内的应用代码，最终 COPY 到镜像的 /nascine
│   ├── app/                 后端（Flask + 调度器），filetransfer.py 是转移核心
│   ├── web/                 前端模板与静态资源，static/css/nascine.css 是主题
│   ├── config/              config.yaml 默认配置、sites.dat、初始化 SQL
│   ├── third_party/         固定版本的依赖（plexapi、slack_bolt、feapder 等）
│   ├── docker/              compose.yml 部署样例
│   └── run.py               入口
├── rootfs/etc  rootfs/root  rootfs/usr    容器系统层（启动脚本、cron）
├── slim/prune.sh            镜像裁剪清单
├── make_slim.py             裁剪 + 扁平化，重导入为单层镜像
├── brand/                   品牌素材
├── make_release.py          图层差分打包脚本
├── release.json             版本号 / 命名空间 / 仓库名
└── build_layer*.py          历次分层构建脚本（历史记录，可忽略）
```

## 构建镜像

本项目不用 Dockerfile，而是**基于一个已有镜像做图层差分**：把 `rootfs/nascine` 与基础镜像对比出增删改，只打一个增量层，因此每次发版的 tar 只有几百 KB。

```bash
# 1. 准备基础镜像（首次从 Docker Hub 拉取，之后用上一版自己的 tar 做基础）
docker pull xdxy/nascine:1.0.6

# 2. 修改代码
vim rootfs/nascine/app/sync.py

# 3. 改版本号后打包
vim release.json          # version: 1.0.6 -> 1.0.7，baseTar 指向上一版 tar
python3 make_release.py   # 输出 ../nascine-1.0.7.tar

# 4. 导入并推送
docker load -i ../nascine-1.0.7.tar
docker push xdxy/nascine:1.0.7
docker tag xdxy/nascine:1.0.7 xdxy/nascine:latest && docker push xdxy/nascine:latest
```

`make_release.py` 支持 `--version`、`--namespace`、`--repository`、`--base`、`--dry-run` 覆盖 `release.json` 的配置。

## 镜像瘦身

1.0.6 起镜像从 2.35 GB 精简到 **681 MB**（`docker pull` 实际下载约 145 MB），做法是裁剪 + 扁平化两步：

```bash
python3 make_slim.py --source xdxy/nascine:1.0.5 --target xdxy/nascine:1.0.6 --version 1.0.6
```

- **裁剪**：`slim/prune.sh` 在容器内删掉运行期没有任何调用路径的组件——chromium / chromedriver（站点签到与索引器已随 PT 模块移除）、gcc 工具链与 C 头文件、`libpython*.a`、Cython / jedi / pygments / prompt_toolkit、rclone、ffmpeg / ffprobe、git / mc、字体、`plexapi` 的测试数据。每一项删除前都核对过调用点。
- **扁平化**：`rm` 在增量层里只留一个 whiteout 标记，原层字节仍在、照样要下载。所以流程是 裁剪层 → `docker export` 拿扁平根文件系统 → `docker import --change` 逐条还原 ENV / ENTRYPOINT / WORKDIR / VOLUME / EXPOSE / LABEL → `docker save`。删掉的字节这才真正消失。

> 之后发版的 `baseTar` 必须指向 `../nascine-1.0.6.tar`，否则新代码会叠回 2.35 GB 的旧基础镜像上。

## 版本对应

镜像 tag 与仓库 tag 一一对应，方便审计「某个镜像到底跑的是哪份代码」：

| 镜像 tag             | 源码 tag   | 说明                        |
| ------------------ | -------- | ------------------------- |
| `1.0.5` / `latest` | `v1.0.5` | 当前线上镜像                    |
| —                  | `v1.0.6` | 镜像瘦身版：源码已发布，镜像待推送（681 MB） |

## 与硬盘休眠共存

NAS（尤其是 Unraid）上最关心的一件事是「容器会不会把机械盘一直唤醒」。程序里只有两个地方会产生**周期性**磁盘访问，其余全部是事件驱动或纯网络请求：

| 访问点 | 频率 | 落在哪块盘 | 处理办法 |
|---|---|---|---|
| TMDB 缓存落盘 | 10 分钟 | `/config/tmdb.dat` | 已改为「内容有变化才写」，空闲时零读写 |
| 目录监控轮询 | 默认 10 秒 | 被监控的目录 | 可配置，见下 |

**关于轮询**：只有监控目录位于 FUSE 挂载（Unraid 的 `/mnt/user`）或 Windows 时才会轮询——这些环境下 inotify 收不到跨容器写入的事件，只能靠扫描。轮询会周期性 `stat` 整个目录树，源目录若在休眠的机械盘上就会持续唤醒它。

控制方式：**系统设置 → 监控轮询间隔（秒）**

| 取值 | 行为 | 适用场景 |
|---|---|---|
| `10`（默认） | 每 10 秒扫描一次 | 源目录在 SSD / 缓存盘，或不在 Unraid |
| `0` | 关闭轮询，改用 inotify 事件监控 | 源目录在阵列盘上、要保住硬盘休眠。**完全无周期性磁盘访问** |
| 其它数值 | 自定义扫描间隔 | 想折中：如 `300`，5 分钟扫一次 |

改为 `0` 后如果发现新文件不被自动转移（某些 FUSE 环境下 inotify 确实收不到事件），说明你的场景必须依赖轮询，那就把间隔调大（如 `600`），或者把下载目录挪到缓存盘后仍用事件监控。

**更彻底的做法**（不需要改代码）：

- `/config` 放缓存盘（Unraid 上即 `/mnt/cache/appdata/nascine`）——所有写入都落在 SSD
- 被监控的下载目录挂 `/mnt/cache/xxx` 而不是 `/mnt/user/xxx`——读到的文件系统不是 `fuse`，自动走 inotify，一次扫描都不会有
- Docker 日志加 `--log-opt max-size=10m --log-opt max-file=3`，避免 stdout 无上限追加

## 许可与致谢

本项目基于 [nas-tools](https://github.com/jxxghp/nas-tools)（作者 [jxxghp](https://github.com/jxxghp)）修改而来，遵循 **AGPL-3.0** 许可，许可证全文见 [`LICENSE`](LICENSE)。

- 上游代码版权归原作者 jxxghp 所有，本仓库的修改同样以 AGPL-3.0 发布。
- 二次分发（包括打包成镜像上传）时，必须一并提供完整源码并保留原始版权声明。
- **AGPL-3.0 第 13 条**：如果你修改本项目后以网络服务的形式提供给他人使用，必须向这些使用者提供修改后的完整源码。

## 免责声明

本项目仅供个人学习与自用，不提供、不内置、不推荐任何影视资源的获取渠道。使用者需自行确保所处理内容的来源合法，并对自己的使用行为负责。作者不对因使用本项目产生的任何直接或间接损失承担责任。
