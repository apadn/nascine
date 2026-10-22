#!/bin/sh
# nascine 容器入口
#
# 本镜像是固定发行版：启动时**不会** git 拉取上游代码（那会覆盖定制界面），
# 升级方式为在宿主机拉取新镜像后重建容器：
#     docker compose pull && docker compose up -d

cd ${WORKDIR}

if [ "${NASCINE_AUTO_UPDATE}" = "true" ]; then
    echo "提示：本镜像不支持程序内自动升级，请执行 docker compose pull 更新镜像。"
fi

echo "以 PUID=${PUID}，PGID=${PGID} 的身份启动程序..."

if [ "${NASCINE_FLAVOR}" = "lite" ]; then
    mkdir -p /.pm2
    chown -R "${PUID}":"${PGID}" "${WORKDIR}" /config /.pm2
else
    mkdir -p /.local
    mkdir -p /.pm2
    chown -R "${PUID}":"${PGID}" "${WORKDIR}" /config /usr/lib/chromium /.local /.pm2
    export PATH=${PATH}:/usr/lib/chromium
fi

umask "${UMASK}"

exec su-exec "${PUID}":"${PGID}" "$(which dumb-init)" "$(which pm2-runtime)" \
    start run.py -n nascine --interpreter python3
