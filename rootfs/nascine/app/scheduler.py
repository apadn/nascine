import datetime
import traceback

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler

import log
from app.downloader import Downloader
from app.helper import MetaHelper
from app.mediaserver import MediaServer
from app.sync import Sync
from app.utils import ExceptionUtils
from app.utils.commons import singleton
from config import PT_TRANSFER_INTERVAL, METAINFO_SAVE_INTERVAL, \
    SYNC_TRANSFER_INTERVAL, META_DELETE_UNKNOWN_INTERVAL, REFRESH_WALLPAPER_INTERVAL, Config
from web.backend.wallpaper import get_login_wallpaper


@singleton
class Scheduler:
    SCHEDULER = None
    _pt = None
    _media = None

    def __init__(self):
        self.init_config()

    def init_config(self):
        self._pt = Config().get_config('pt')
        self._media = Config().get_config('media')

    def run_service(self):
        """
        读取配置，启动定时服务
        说明：站点签到、站点数据刷新、RSS 订阅检索、豆瓣同步等 PT / 内容发现类定时任务
        已随对应模块一并移除，此处只保留影音库自身运转所需的服务
        """
        self.SCHEDULER = BackgroundScheduler(timezone=Config().get_timezone(),
                                             executors={
                                                 'default': ThreadPoolExecutor(20)
                                             })
        if not self.SCHEDULER:
            return

        # 下载文件转移
        if self._pt:
            pt_monitor = self._pt.get('pt_monitor')
            if pt_monitor:
                self.SCHEDULER.add_job(Downloader().transfer, 'interval', seconds=PT_TRANSFER_INTERVAL)
                log.info("下载文件转移服务启动")

        # 媒体库同步
        if self._media:
            mediasync_interval = self._media.get("mediasync_interval")
            if mediasync_interval:
                if isinstance(mediasync_interval, str):
                    if mediasync_interval.isdigit():
                        mediasync_interval = int(mediasync_interval)
                    else:
                        try:
                            mediasync_interval = round(float(mediasync_interval))
                        except Exception as e:
                            log.info("媒体库同步周期配置错误：%s" % str(e))
                            mediasync_interval = 0
                if mediasync_interval:
                    self.SCHEDULER.add_job(MediaServer().sync_mediaserver, 'interval', hours=mediasync_interval)
                    log.info("媒体库同步服务启动")

        # 元数据定时保存
        self.SCHEDULER.add_job(MetaHelper().save_meta_data, 'interval', seconds=METAINFO_SAVE_INTERVAL)

        # 定时把队列中的监控文件转移走
        self.SCHEDULER.add_job(Sync().transfer_mon_files, 'interval', seconds=SYNC_TRANSFER_INTERVAL)

        # 定时清除未识别的缓存
        self.SCHEDULER.add_job(MetaHelper().delete_unknown_meta, 'interval', hours=META_DELETE_UNKNOWN_INTERVAL)

        # 定时刷新壁纸
        self.SCHEDULER.add_job(get_login_wallpaper,
                               'interval',
                               hours=REFRESH_WALLPAPER_INTERVAL,
                               next_run_time=datetime.datetime.now())

        self.SCHEDULER.print_jobs()

        self.SCHEDULER.start()

    def stop_service(self):
        """
        停止定时服务
        """
        try:
            if self.SCHEDULER:
                self.SCHEDULER.remove_all_jobs()
                self.SCHEDULER.shutdown()
                self.SCHEDULER = None
        except Exception as e:
            ExceptionUtils.exception_traceback(e)


def run_scheduler():
    """
    启动定时服务
    """
    try:
        Scheduler().run_service()
    except Exception as err:
        log.error("启动定时服务失败：%s - %s" % (str(err), traceback.format_exc()))


def stop_scheduler():
    """
    停止定时服务
    """
    try:
        Scheduler().stop_service()
    except Exception as err:
        log.debug("停止定时服务失败：%s" % str(err))


def restart_scheduler():
    """
    重启定时服务
    """
    stop_scheduler()
    run_scheduler()
