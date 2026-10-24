import datetime
import re
from abc import ABCMeta, abstractmethod


def parse_utc_time(date_str):
    """
    解析媒体服务器返回的UTC时间字符串（如 2026-10-24T14:30:00.0000000Z），
    转换为带时区的本地时间对象，解析失败返回None
    """
    if not date_str:
        return None
    # 去掉小数秒（Emby/Jellyfin 会返回7位），保留时区后缀
    text = re.sub(r'\.\d+', '', str(date_str).strip())
    try:
        dt = datetime.datetime.fromisoformat(text.replace('Z', '+00:00'))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.astimezone()


def format_play_time(dt):
    """
    把播放时间格式化为「今天 21:30」「昨天 21:30」「10-22 21:30」这样的友好文本
    """
    if not dt:
        return ""
    now = datetime.datetime.now(dt.tzinfo)
    days = (now.date() - dt.date()).days
    if days == 0:
        return "今天 %s" % dt.strftime('%H:%M')
    if days == 1:
        return "昨天 %s" % dt.strftime('%H:%M')
    if dt.year == now.year:
        return dt.strftime('%m-%d %H:%M')
    return dt.strftime('%Y-%m-%d %H:%M')


def format_play_clock(dt):
    """
    事件流的时刻：当天的只给「21:30:05」，昨天加前缀，更早给「10-22 21:30」
    """
    if not dt:
        return ""
    now = datetime.datetime.now(dt.tzinfo)
    days = (now.date() - dt.date()).days
    if days == 0:
        return dt.strftime('%H:%M:%S')
    if days == 1:
        return "昨天 %s" % dt.strftime('%H:%M')
    if dt.year == now.year:
        return dt.strftime('%m-%d %H:%M')
    return dt.strftime('%Y-%m-%d %H:%M')


# 各版本媒体服务器的播放事件类型，统一归一化成 start / stop
PLAY_START_TYPES = (
    "videoplayback",          # Emby < 4.9 / Jellyfin
    "audioplayback",
    "playback.start",         # Emby >= 4.9（活动日志与通知统一后的新类型）
    "playbackstart",
)
PLAY_STOP_TYPES = (
    "videoplaybackstopped",
    "audioplaybackstopped",
    "playback.stop",
    "playbackstop",
)


def parse_play_event_type(event_type):
    """
    把活动日志的 Type 归一化成 start / stop，非播放事件返回 None
    """
    text = (event_type or "").strip().lower()
    if text in PLAY_START_TYPES:
        return "start"
    if text in PLAY_STOP_TYPES:
        return "stop"
    return None


def fill_play_duration(events):
    """
    按时间正序的播放事件里，用 start/stop 配对补出「本次播放多久」，
    事件自身已带时长说明（ShortOverview）时不覆盖
    """
    starts = {}
    for event in events:
        key = (event.get("user_id"), event.get("item_id"))
        if event.get("type") == "start":
            starts[key] = event.get("timestamp")
        elif event.get("type") == "stop":
            begin = starts.pop(key, None)
            if begin and not event.get("detail") and event.get("timestamp", 0) > begin:
                minutes = max(1, int(round((event["timestamp"] - begin) / 60.0)))
                event["detail"] = "本次播放 %d 分钟" % minutes


class _IMediaClient(metaclass=ABCMeta):

    @abstractmethod
    def match(self, ctype):
        """
        匹配实例
        """
        pass

    @abstractmethod
    def get_status(self):
        """
        检查连通性
        """
        pass

    @abstractmethod
    def get_user_count(self):
        """
        获得用户数量
        """
        pass

    @abstractmethod
    def get_activity_log(self, num):
        """
        获取Emby活动记录
        """
        pass

    @abstractmethod
    def get_medias_count(self):
        """
        获得电影、电视剧、动漫媒体数量
        :return: MovieCount SeriesCount SongCount
        """
        pass

    @abstractmethod
    def get_movies(self, title, year):
        """
        根据标题和年份，检查电影是否在存在，存在则返回列表
        :param title: 标题
        :param year: 年份，可以为空，为空时不按年份过滤
        :return: 含title、year属性的字典列表
        """
        pass

    @abstractmethod
    def get_no_exists_episodes(self, meta_info, season, total_num):
        """
        根据标题、年份、季、总集数，查询缺少哪几集
        :param meta_info: 已识别的需要查询的媒体信息
        :param season: 季号，数字
        :param total_num: 该季的总集数
        :return: 该季不存在的集号列表
        """
        pass

    @abstractmethod
    def get_image_by_id(self, item_id, image_type):
        """
        根据ItemId查询图片地址
        :param item_id: 在服务器中的ID
        :param image_type: 图片的类弄地，poster或者backdrop等
        :return: 图片对应在TMDB中的URL
        """
        pass

    @abstractmethod
    def refresh_root_library(self):
        """
        刷新整个媒体库
        """
        pass

    @abstractmethod
    def refresh_library_by_items(self, items):
        """
        按类型、名称、年份来刷新媒体库
        :param items: 已识别的需要刷新媒体库的媒体信息列表
        """
        pass

    @abstractmethod
    def get_libraries(self):
        """
        获取媒体服务器所有媒体库列表
        """
        pass

    @abstractmethod
    def get_items(self, parent):
        """
        获取媒体库中的所有媒体
        :param parent: 上一级的ID
        """
        pass

    @abstractmethod
    def get_playing_sessions(self):
        """
        获取正在播放的会话
        """
        pass

    @abstractmethod
    def get_play_history(self, num=40):
        """
        获取最近播放记录
        :param num: 返回条数
        :return: 播放记录字典列表（title/type/user/played_at/percent/timestamp）
        """
        pass
