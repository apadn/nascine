# nascine

**极简苹果风 · 个人影音库中枢 —— 下载 → 整理 → 刮削，一条主线自动化**

`nascine = nas + cinema` ｜ 基于 NAS-Tools 2.9.1 重制的定制发行版

---

## 它是什么

nascine 只做一件事：**你下载完，剩下的交给它**。

文件落地后自动按类型转移到电影 / 剧集目录、按规范重命名、识别并刮削元数据（nfo、海报、背景图），最后通知 Emby / Jellyfin / Plex 刷新媒体库。没有站点管理、没有订阅、没有探索榜单，也没有需要你手工点的手动整理——界面重做成极简的苹果风，把注意力留给片库本身。

上游 NAS-Tools 的学习成本主要来自「功能太多」：PT 站点、刷流、索引器、订阅、豆瓣同步、网盘模式、硬链接、Rclone……nascine 把这些整体切掉，只保留真正每天在跑的那条流水线，因此配置项更少、出错面更小，也不再需要理解一堆概念才能用起来。

## 主要功能

| 模块 | 能力 |
| --- | --- |
| **下载监控** | 对接 qBittorrent / Transmission，任务完成后自动触发转移 |
| **自动整理** | 按类型分类、重命名、TMDb 识别，支持自定义识别词纠正误判 |
| **媒体刮削** | 生成 nfo、下载海报与背景图，命名与目录结构符合 Emby / Jellyfin / Plex 约定 |
| **媒体库同步** | 定时通知媒体服务器刷新，或直接调用其 API 触发扫描 |
| **消息通知** | 企业微信、Telegram、Slack、Synology Chat、Bark、Gotify、Server 酱、PushDeer、PushPlus、Chanify、IYUU |
| **下载器** | qBittorrent、Transmission（界面另保留 115、Aria2、PikPak 客户端配置项） |
| **转移方式** | 只有「复制」与「移动」两种，不再有硬链接 / Rclone / Minio / 网盘模式 |
| **定时任务** | 只保留转移监控、媒体库同步、元数据保存与清理、登录壁纸等必要任务 |

界面只留四组入口：**我的媒体库 / 下载管理 / 服务 / 设置**，侧栏不再有十几个入口需要辨认。

## 与上游的主要差异

- 移除 PT 站点、刷流、索引器、探索榜单、资源搜索、订阅管理、豆瓣同步
- **媒体整理整组下线**：文件管理、手动识别、历史记录、TMDB 缓存四个页面连同后端路由一并删除，整理完全由「下载完成 → 目录同步」自动完成
- 转移方式收敛为复制 / 移动
- **不内置任何第三方服务地址**：没有作者提供的 TMDB 代理、OCR、CookieCloud、微信消息代理。TMDB 直连你在「基础设置」里选择的官方域名；需要 OCR 时自行部署，用 `NASCINE_OCR_SERVER` 指定
- **不做 git 自动更新**：启动时不会 `git reset --hard`，升级只通过 `docker pull`
- 容器内代码目录为 `/nascine`（`site-packages/nascine.pth` 同步指向它），进程名、日志、界面均为 `nascine`

## 快速开始

### docker compose（推荐）

```yaml
services:
  nascine:
    image: xdxy/nascine:latest
    container_name: nascine
    hostname: nascine
    restart: unless-stopped
    ports:
      - 3000:3000
    volumes:
      - ./config:/config                # 配置与数据库
      - /mnt/user/downloads:/downloads  # 下载目录，按实际情况修改
      - /mnt/user/media:/media          # 媒体库根目录，按实际情况修改
    environment:
      - PUID=99                  # 与 qBittorrent / Emby 的 PUID 保持一致
      - PGID=100
      - UMASK=002
      - TZ=Asia/Shanghai
      - NASCINE_IMAGE_REPO=xdxy/nascine
      - NASCINE_UPDATE_MODE=docker
```

```bash
docker compose up -d
```

### docker run

```bash
docker run -d \
    --name nascine \
    --hostname nascine \
    -p 3000:3000 \
    -v $(pwd)/config:/config \
    -v /你的下载目录:/downloads \
    -v /你的媒体目录:/media \
    -e PUID=99 \
    -e PGID=100 \
    -e UMASK=002 \
    -e TZ=Asia/Shanghai \
    xdxy/nascine:latest
```

启动后访问 `http://<NAS_IP>:3000`，默认账号 `admin` / `password`，**首次登录请立即修改密码**。

> 挂载路径必须与「设置 → 目录同步」里填写的容器内路径一致（`/downloads`、`/media`）。
> `PUID` / `PGID` 必须与下载器、媒体服务器容器完全相同，否则转移出的文件会没有读写权限（`id -u`、`id -g` 可查）。

## 端口与卷

| 项目 | 值 | 说明 |
| --- | --- | --- |
| 端口 | `3000/tcp` | Web 界面与 API（`/api/v1/`） |
| 卷 | `/config` | 配置 `config.yaml`、数据库、日志，**必须持久化** |
| 卷 | `/downloads` | 下载目录，与下载器共享同一路径 |
| 卷 | `/media` | 媒体库根目录，与媒体服务器共享同一路径 |

## 环境变量

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `PUID` / `PGID` | `0` / `0` | 运行身份，务必与下载器、媒体服务器一致 |
| `UMASK` | `000` | 文件权限掩码，`002` 让同组可写 |
| `TZ` | `Asia/Shanghai` | 时区 |
| `NASCINE_CONFIG` | `/config/config.yaml` | 配置文件路径 |
| `NASCINE_LOG` | 配置同级 `logs` | 日志目录 |
| `NASCINE_IMAGE_REPO` | `xdxy/nascine` | 版本检查用的仓库，仅影响「有新版本」提示 |
| `NASCINE_UPDATE_MODE` | `docker` | `docker`（只提示拉取新镜像）/ `github` / `off` |
| `NASCINE_FLAVOR` | `full` | `lite` 时跳过 chromium 初始化，无浏览器抓取需求可设 |
| `NASCINE_OCR_SERVER` | 空 | 自建 OCR 服务地址，未设置则完全不发外部请求 |

## 升级

```bash
docker compose pull && docker compose up -d
```

配置保存在 `/config` 卷里，重建容器不会丢。因为不做 git 自更新，侧栏底部的「更新」按钮只会提示新版本 tag 和 `docker pull` 命令，不会改动镜像内任何文件。

## 从 NAS-Tools 迁移

配置结构、数据库、媒体目录映射都不变，把原来的配置目录直接挂过来即可，只需替换镜像与容器名：

| 项目 | 原版 | nascine |
| --- | --- | --- |
| 镜像 | 原镜像 | `xdxy/nascine:latest` |
| 容器名 / 主机名 | `nas-tools` | `nascine` |
| 环境变量 | `NASTOOL_*` | 统一改为 `NASCINE_*`（`AUTO_UPDATE` / `CN_UPDATE` / `REPO_URL` 已不需要） |
| 下载任务标签 | `NASTOOL` | `NASCINE` |
| 转移方式 | 硬链接 / Rclone / Minio 等 | 仅复制 / 移动（旧配置里的其它值按「复制」处理） |

> 代码目录已从 `/nas-tools` 改为 `/nascine`，若你有自定义脚本引用了旧路径，请一并修改。

## 镜像信息

- 基础：Alpine + Python 3 + pm2，非 root 运行（`su-exec` 降权），支持 `umask`
- 架构：`linux/amd64`（arm64 设备可用 `--platform linux/amd64` 以 QEMU 模拟运行）
- 标签：`1.0.6`、`latest`
- 体积：解压后约 2.3 GB，主要来自 chromium 与编译期依赖；不需要浏览器抓取时可用 `NASCINE_FLAVOR=lite` 跳过其初始化

## 关于隐私

镜像内**没有任何写死的第三方服务地址**：无 TMDB 代理、无 OCR 服务、无 CookieCloud 服务器、无微信消息中转。所有对外请求都由你在设置里填的地址决定，或直连官方域名；OCR 未配置 `NASCINE_OCR_SERVER` 时不会发出任何请求。

## 许可与致谢

界面与后端改动基于 [NAS-Tools](https://github.com/jxxghp/nas-tools) 2.9.1（MIT），原始版权归其作者所有。本项目为非官方定制发行版，与上游作者无关，请勿向上游仓库反馈本镜像的问题。

---

问题反馈 / 功能建议请在本镜像页面的 Comments 区留言。
