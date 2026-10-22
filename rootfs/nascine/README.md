# nascine

个人影音库中枢 —— 下载 → 整理 → 刮削，一站式自动化。

nascine 取自 **nas** + **cinema**，基于 NAS-Tools 2.9.1 重制：界面改为极简苹果风布局，
并切掉了 PT 站点、刷流、索引器、探索榜单、资源搜索、订阅管理、豆瓣同步等模块，
只保留「影片下载完 → 自动分类转移 → 重命名 → 刮削入库」这条主线。
媒体整理（文件管理 / 手动识别 / 历史记录 / TMDB 缓存）整组不再提供，一切由目录同步自动完成。

![nascine](web/static/img/logo.png)

## 功能

- **下载监控**：对接 qBittorrent / Transmission，种子完成后自动触发转移
- **文件整理**：按类型自动分类、重命名、支持 TMDb 识别与自定义识别（全自动，无手工整理界面）
- **媒体刮削**：生成 nfo、下载海报与背景图，媒体服务器（Emby / Jellyfin / Plex）可直接识别
- **媒体库同步**：定时通知媒体服务器刷新，或调用其 API 更新
- **消息通知**：企业微信 / Telegram / Slack / Synology Chat 等渠道
- **定时任务**：仅保留 5 个必要任务（转移监控、媒体库同步、元数据保存与清理、登录壁纸）
- **转移方式**：仅「复制」与「移动」两种，不再有硬链接 / Rclone / Minio / 网盘模式
- **零内置服务**：不含任何第三方 TMDB 代理 / OCR / CookieCloud / 微信消息代理，全部走官方直连或自建

## 安装

### Docker（推荐）

```
docker pull xdxy/nascine:1.0.5
```

部署细节见 [docker/readme.md](docker/readme.md) 。

镜像为固定发行版，**不执行 git 更新**，升级方式为拉取新镜像后重建容器。

### 本地运行

需要 Python 3.10，并预装 cython，缺少依赖包需自行安装：

```
python3 -m pip install -r requirements.txt
export NASCINE_CONFIG="/xxx/config/config.yaml"
nohup python3 run.py &
```

## 环境变量

| 变量 | 说明 |
| --- | --- |
| `NASCINE_CONFIG` | 配置文件路径，Docker 内为 `/config/config.yaml` |
| `NASCINE_LOG` | 日志目录，默认与配置文件同级的 `logs` |
| `NASCINE_IMAGE_REPO` | 版本检查用的镜像仓库，默认 `xdxy/nascine` |
| `NASCINE_UPDATE_MODE` | `docker`（只提示拉取新镜像）/ `off` |
| `NASCINE_FLAVOR` | `full`（默认，含 chromium）/ `lite` |
| `PUID` / `PGID` / `UMASK` | 运行身份与文件权限掩码 |

## API

`http://<ip>:3000/api/v1/`（需在设置中生成 ApiKey）

## 许可

界面与后端改动基于 NAS-Tools（MIT），原始版权归其作者所有，详见 [LICENSE.md](LICENSE.md)。
