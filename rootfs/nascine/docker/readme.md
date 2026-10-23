## nascine 说明

nascine = nas + cinema，一个只做「下载 → 整理 → 刮削」的个人影音库中枢，界面为极简苹果风。

镜像基于 NAS-Tools 2.9.1 重制并大幅裁剪：

- 移除 PT 站点 / 刷流 / 索引器 / 探索榜单 / 资源搜索 / 订阅管理 / 豆瓣同步等模块
- **媒体整理整组下线**：文件管理、手动识别、历史记录、TMDB 缓存四个页面连同路由一起删除，
  整理行为完全由「下载完成 → 目录同步」自动完成
- 文件转移方式收敛为「复制 / 移动」两种，不再有硬链接 / Rclone / Minio / 网盘模式
- 下线站点签到、站点数据刷新、RSS 拉取、订阅检索等定时任务，后台只剩 5 个必要任务
- **不内置任何第三方服务地址**：没有作者提供的 TMDB 代理、OCR、CookieCloud、微信消息代理，
  TMDB 直连你在「基础设置」里选的官方域名；需要 OCR 时自行部署并通过 `NASCINE_OCR_SERVER` 指定
- **不执行 git 更新**：启动时不会 `git reset --hard`，升级只通过 `docker pull`
- 容器内代码目录为 `/nascine`（`site-packages/nascine.pth` 同步指向它）

## 特点

- 基于 alpine 实现，镜像体积小

- 支持 amd64/arm64 架构

- 可以以非 root 用户执行任务，降低程序权限和潜在风险

- 可以设置文件掩码权限 umask

- 版本检查指向 `xdxy/nascine` 的 Docker Hub 仓库，界面提示有新版本后由你自己 `docker pull`，
  程序内不会改动任何文件

## 创建

**注意**

- 媒体目录的设置必须符合「系统设置 → 媒体库」中的目录约定（电影/电视剧分别指向各自根目录）。

- umask 含义详见：http://www.01happy.com/linux-umask-analyze 。

- 创建后请按 `config/config.yaml` 本身的注释修改配置，改好后再重启容器，最后访问 `http://<ip>:<web_port>`。

**docker cli**

```
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
    -e NASCINE_IMAGE_REPO=xdxy/nascine \
    -e NASCINE_UPDATE_MODE=docker \
    xdxy/nascine:1.0.6
```

- `-v` 左边改成你在宿主机上的真实路径，冒号右边是容器内路径，要与「系统设置 → 目录同步」里填的路径一致。
- `PUID` / `PGID` 取 `id -u` / `id -g`，且必须与下载器、媒体服务器保持一致。
- `NASCINE_IMAGE_REPO` / `NASCINE_UPDATE_MODE` 用于版本检查；不填不影响运行。

**docker-compose**

直接用同目录下的 `compose.yml`：

```bash
docker compose pull     # 或者 docker load -i nascine-1.0.6.tar
docker compose up -d
```

## 后续如何更新

```
docker compose pull && docker compose up -d
```

或手工：

```bash
docker pull xdxy/nascine:1.0.6
docker stop nascine && docker rm nascine   # 配置在 /config 卷里，不会丢
docker run ...                              # 用上面同样的参数重建
```

版本号可以在侧栏底部看到（当前 `v1.0.6`）。程序内的「更新」按钮只会提示新版本 tag 与 `docker pull` 命令，
不会自己下载或改动文件。

## 关于 PUID/PGID 的说明

- 如在使用诸如 emby、jellyfin、plex、qbittorrent、transmission、deluge、jackett、sonarr、radarr 等等的 docker 镜像，
  请保证创建本容器时的 PUID/PGID 和它们一样。

- 在 docker 宿主上，登录媒体文件所有者的这个用户，然后分别输入 `id -u` 和 `id -g` 可获取到 uid 和 gid，
  分别设置为 PUID 和 PGID 即可。

- `PUID=0` `PGID=0` 指 root 用户，它拥有最高权限，若你的媒体文件的所有者不是 root，不建议设置为 `PUID=0` `PGID=0`。
  本镜像的 compose 示例默认给的是 Unraid 的 `99:100`。

## 从旧版部署迁移

配置结构、数据库、媒体目录映射都不变，把原来的配置目录原样挂过来即可，只需替换：

| 项目 | 原版 | nascine |
| --- | --- | --- |
| `image` | 旧镜像 | `xdxy/nascine:1.0.6` |
| 容器名 / 主机名 | `nas-tools`（旧） | `nascine` |
| 版本检查变量 | 无 | `NASCINE_IMAGE_REPO=xdxy/nascine`、`NASCINE_UPDATE_MODE=docker` |
| `NASTOOL_*` 环境变量 | 有 | 统一改为 `NASCINE_*`（`AUTO_UPDATE` / `CN_UPDATE` / `REPO_URL` 已不需要） |
| 转移方式 | 硬链接 / 复制 / 移动 / Rclone / Minio | 仅复制 / 移动（旧配置中的其它值按「复制」处理） |
| 下载任务标签 | `NASTOOL` | `NASCINE` |

> 容器内的代码目录已由 `/nas-tools` 改为 `/nascine`，基础镜像层里的路径与 `site-packages/nascine.pth` 都已同步重写，如果你有自定义脚本引用了旧路径，请一并改成 `/nascine`。
> 程序名、界面、日志、进程名、镜像标签均为 `nascine`。
