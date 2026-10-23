#!/bin/sh
# nascine 镜像裁剪脚本（在容器内执行，由 make_slim.py 注入到临时 Dockerfile）
#
# 原则：只删「没有任何调用路径」或「仅构建期需要」的东西，不改动应用代码。
# 每一项后面注明为什么可以删，改动前请先确认对应模块没被重新启用。

set -u

# ---------------------------------------------------------------------------
# 1) Chromium / chromedriver：248 MB
#    仅供站点签到、站点 Cookie 获取、索引器渲染爬虫使用（selenium + undetected_chromedriver）。
#    nascine 已移除 PT 站点与资源搜索模块，UI 里也没有入口；ChromeHelper 里有
#    `if not uc.find_chrome_executable(): return` 的保护，找不到浏览器会直接跳过。
#    保留空目录，因为 entrypoint.sh 会对 /usr/lib/chromium 做 chown，目录不存在会报错。
# ---------------------------------------------------------------------------
rm -rf /usr/lib/chromium/*
mkdir -p /usr/lib/chromium

# ---------------------------------------------------------------------------
# 2) gcc 工具链 + C 头文件：约 120 MB
#    只有「在容器里现编译 Python 扩展」时才需要。镜像里所有依赖都是预编译好的，
#    运行期不会编译任何东西。
# ---------------------------------------------------------------------------
rm -rf /usr/libexec/gcc /usr/lib/gcc /usr/include
rm -f /usr/bin/gcc /usr/bin/g++ /usr/bin/cpp /usr/bin/cc /usr/bin/c++ \
      /usr/bin/lto-dump /usr/bin/dwp /usr/bin/gcc-ar /usr/bin/gcc-nm /usr/bin/gcc-ranlib

# ---------------------------------------------------------------------------
# 3) Python 静态库与构建配置：47 MB
#    libpython3.10.a 是给「二次开发时链接 libpython」用的，运行期完全不需要。
# ---------------------------------------------------------------------------
rm -rf /usr/lib/python3.10/config-3.10-x86_64-linux-gnu

# ---------------------------------------------------------------------------
# 4) Python 标准库里用不到的子集：约 6 MB
# ---------------------------------------------------------------------------
rm -rf /usr/lib/python3.10/lib2to3 /usr/lib/python3.10/ensurepip /usr/lib/python3.10/idlelib

# ---------------------------------------------------------------------------
# 5) 开发/交互类第三方包：约 33 MB
#    Cython 是编译器，jedi / pygments / prompt_toolkit 是交互式终端的补全与高亮；
#    Web 端与后台任务都不依赖它们（flask_restx 的 apidoc 已验证不受影响）。
# ---------------------------------------------------------------------------
rm -rf /usr/lib/python3.10/site-packages/Cython \
       /usr/lib/python3.10/site-packages/jedi \
       /usr/lib/python3.10/site-packages/pygments \
       /usr/lib/python3.10/site-packages/prompt_toolkit

# ---------------------------------------------------------------------------
# 6) npm 缓存 / mc / git：约 50 MB
#    node 与 pm2 必须保留（entrypoint 用 pm2-runtime 拉起 run.py）；
#    /root/.npm 是安装 pm2 时的下载缓存，mc 是交互式文件管理器，
#    git 只服务于已移除的「程序内更新」逻辑。
# ---------------------------------------------------------------------------
rm -rf /root/.npm /usr/bin/mc /usr/libexec/git-core /usr/share/git-core /usr/bin/git

# ---------------------------------------------------------------------------
# 7) rclone：48 MB
#    对外的转移方式只有「复制 / 移动」（ModuleConf.RMT_MODES_SIMPLE），
#    UI 无法触发 rclone / rclonecopy，二进制没有调用入口。
# ---------------------------------------------------------------------------
rm -f /usr/bin/rclone

# ---------------------------------------------------------------------------
# 8) ffmpeg / ffprobe 及其依赖的 libav*：约 25 MB
#    代码里没有任何 ffmpeg / ffprobe 调用（刮削与识别走 TMDB API，不做转码）。
#    注意：只删 libavcodec/libavformat/libavfilter/libavdevice/libavutil/
#    libpostproc/libswscale/libswresample，不要用 libav* 通配，会误删 libavahi。
# ---------------------------------------------------------------------------
rm -f /usr/bin/ffmpeg /usr/bin/ffprobe
rm -f /usr/lib/libavcodec.so* /usr/lib/libavformat.so* /usr/lib/libavfilter.so* \
      /usr/lib/libavdevice.so* /usr/lib/libavutil.so* /usr/lib/libpostproc.so* \
      /usr/lib/libswscale.so* /usr/lib/libswresample.so*

# ---------------------------------------------------------------------------
# 9) 字体：9 MB（只被 Chromium 渲染页面时使用）
# ---------------------------------------------------------------------------
rm -rf /usr/share/fonts

# ---------------------------------------------------------------------------
# 10) 应用内的测试数据与字节码：约 22 MB
#     plexapi 自带 18 MB 的 video_stub.mp4 / audio_stub.mp3，只供其单元测试使用。
# ---------------------------------------------------------------------------
rm -rf /nascine/third_party/plexapi/tests
find /nascine -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null
find /nascine -name '*.pyc' -type f -delete 2>/dev/null

echo "[slim] rootfs 裁剪完成：$(du -sm / 2>/dev/null | cut -f1) MB"
