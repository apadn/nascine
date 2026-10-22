# nascine

极简 · 苹果风的个人影音库中枢：**下载 → 整理 → 刮削**，一个容器跑完。

nascine 是 [nas-tools](https://github.com/jxxghp/nas-tools) 的精简定制版：保留媒体库、下载管理、目录同步、服务与系统设置，
去掉 PT 站点、探索、资源搜索、订阅、豆瓣同步等模块，转移方式只保留「复制」和「移动」，
不内置任何第三方代理、OCR、CookieCloud 服务。UI 整体重做成 iOS / macOS 风格的浅色主题。

## 功能范围

| 保留 | 已移除 |
|---|---|
| 媒体库（电影 / 剧集 / 动漫）与刮削 | PT 站点、做种、刷流 |
| qBittorrent / Transmission / Aria2 / 115 等下载器 | 资源搜索、站点索引 |
| 目录同步（监控目录自动识别改名转移） | 订阅、RSS 自动下载 |
| 消息通知、自定义识别词、过滤规则 | 豆瓣同步、媒体整理（硬链接整理） |
| 服务控制、系统设置、版本更新提示 | 第三方代理 / OCR / CookieCloud 内置服务 |

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
├── brand/                   品牌素材
├── make_release.py          图层差分打包脚本
├── release.json             版本号 / 命名空间 / 仓库名
└── build_layer*.py          历次分层构建脚本（历史记录，可忽略）
```

## 构建镜像

本项目不用 Dockerfile，而是**基于一个已有镜像做图层差分**：把 `rootfs/nascine` 与基础镜像对比出增删改，
只打一个增量层，因此每次发版的 tar 只有几百 KB。

```bash
# 1. 准备基础镜像（首次从 Docker Hub 拉取，之后用上一版自己的 tar 做基础）
docker pull xdxy/nascine:1.0.5

# 2. 修改代码
vim rootfs/nascine/app/sync.py

# 3. 改版本号后打包
vim release.json          # version: 1.0.5 -> 1.0.6，baseTar 指向上一版 tar
python3 make_release.py   # 输出 ../nascine-1.0.6.tar

# 4. 导入并推送
docker load -i ../nascine-1.0.6.tar
docker push xdxy/nascine:1.0.6
docker tag xdxy/nascine:1.0.6 xdxy/nascine:latest && docker push xdxy/nascine:latest
```

`make_release.py` 支持 `--version`、`--namespace`、`--repository`、`--base`、`--dry-run` 覆盖 `release.json` 的配置。

## 运行

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

或直接使用 `rootfs/nascine/docker/compose.yml`。启动后访问 `http://<ip>:3000`，默认账号 `admin` / 密码 `password`，登录后请立即修改。

## 版本号约定

`version.py` 由 `make_release.py` 依据 `release.json` 生成，格式为 `v<APP_VERSION_BASE><APP_VERSION_REVISION>`，请勿手改。

## 许可与致谢

本项目基于 [nas-tools](https://github.com/jxxghp/nas-tools)（作者 jxxghp）修改而来，遵循 **AGPL-3.0** 许可，
详见 [`rootfs/nascine/LICENSE.md`](rootfs/nascine/LICENSE.md)。二次分发与网络部署时请同样开源修改后的代码，
并保留原始版权声明。
