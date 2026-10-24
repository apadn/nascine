# nascine

[![Docker Pulls](https://img.shields.io/docker/pulls/xdxy/nascine)](https://hub.docker.com/r/xdxy/nascine)
[![Image Version](https://img.shields.io/docker/v/xdxy/nascine/latest?label=image)](https://hub.docker.com/r/xdxy/nascine/tags)
[![License: AGPL v3](https://img.shields.io/badge/license-AGPL--3.0-blue.svg)](LICENSE)
![Platform](https://img.shields.io/badge/platform-linux%2Famd64-lightgrey)

极简 · 苹果风的个人影音库中枢：**下载 → 整理 → 刮削**，一个容器跑完。

下载器里的文件落地后，nascine 会自动识别剧名 / 季集、按 TMDB 元数据重命名、刮削封面与简介，并按「电影 / 剧集 / 动漫」归档到媒体库目录。全程在 Web 界面上配置，不需要改配置文件。

## 这是什么

nascine 是 [nas-tools](https://github.com/jxxghp/nas-tools) 的精简定制版：保留媒体库、下载管理、目录同步、服务与系统设置，去掉 PT 站点、探索、资源搜索、订阅、豆瓣同步等模块，转移方式只保留「复制」和「移动」，不内置任何第三方代理、OCR、CookieCloud 服务。UI 整体重做成 iOS / macOS 风格的浅色主题。

它只做一件事：**把下载好的文件整理进媒体库**。鉴权、下载、播放交给 qBittorrent / Transmission / Emby / Jellyfin 这些专业工具。

## 功能范围

| 保留 | 已移除 |
|---|---|
| 媒体库（电影 / 剧集 / 动漫）与刮削 | PT 站点、做种、刷流 |
| qBittorrent / Transmission / Aria2 / 115 等下载器 | 资源搜索、站点索引 |
| 目录同步（监控目录自动识别改名转移） | 订阅、RSS 自动下载 |
| 消息通知、自定义识别词、过滤规则 | 豆瓣同步、媒体整理（硬链接整理） |
| 服务控制、系统设置、版本更新提示 | 第三方代理 / OCR / CookieCloud 内置服务 |

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

| 容器内路径 | 用途 | 说明 |
|---|---|---|
| `/config` | 配置、SQLite 数据库、日志 | 必须持久化，否则重建容器后配置全丢 |
| `/downloads` | 下载器的输出目录 | 与下载器指向同一个宿主机目录，nascine 才能监控到文件 |
| `/media` | 媒体库根目录 | 刮削后的文件归档到这里，供 Emby / Jellyfin 扫描 |

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

## 许可与致谢

本项目基于 [nas-tools](https://github.com/jxxghp/nas-tools)（作者 [jxxghp](https://github.com/jxxghp)）修改而来，遵循 **AGPL-3.0** 许可，许可证全文见 [`LICENSE`](LICENSE)。

- 上游代码版权归原作者 jxxghp 所有，本仓库的修改同样以 AGPL-3.0 发布。
- 二次分发（包括打包成镜像上传）时，必须一并提供完整源码并保留原始版权声明。
- **AGPL-3.0 第 13 条**：如果你修改本项目后以网络服务的形式提供给他人使用，必须向这些使用者提供修改后的完整源码。

## 免责声明

本项目仅供个人学习与自用，不提供、不内置、不推荐任何影视资源的获取渠道。使用者需自行确保所处理内容的来源合法，并对自己的使用行为负责。作者不对因使用本项目产生的任何直接或间接损失承担责任。
