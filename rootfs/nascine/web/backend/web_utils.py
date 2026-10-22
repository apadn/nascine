import os
import re

import cn2an

from app.media import Media, Bangumi, DouBan
from app.media.meta import MetaInfo
from app.utils import StringUtils, ExceptionUtils, SystemUtils, RequestUtils
from app.utils.types import MediaType
from config import Config
from version import APP_VERSION


class WebUtils:

    @staticmethod
    def get_location(ip):
        """
        根据IP址查询真实地址
        """
        url = 'https://sp0.baidu.com/8aQDcjqpAAV3otqbppnN2DJv/api.php?co=&resource_id=6006&t=1529895387942&ie=utf8' \
              '&oe=gbk&cb=op_aladdin_callback&format=json&tn=baidu&' \
              'cb=jQuery110203920624944751099_1529894588086&_=1529894588088&query=%s' % ip
        r = RequestUtils().get_res(url)
        r.encoding = 'gbk'
        html = r.text
        try:
            c1 = html.split('location":"')[1]
            c2 = c1.split('","')[0]
            return c2
        except Exception as err:
            ExceptionUtils.exception_traceback(err)
            return ""

    @staticmethod
    def get_update_mode():
        """
        更新方式：docker（默认，拉取新镜像）/ github（Release 检查）/ off（关闭）
        """
        return str(os.environ.get("NASCINE_UPDATE_MODE") or "docker").strip().lower()

    @staticmethod
    def get_image_repo():
        """
        当前镜像仓库，如 xdxy/nascine
        """
        repo = str(os.environ.get("NASCINE_IMAGE_REPO") or "xdxy/nascine").strip()
        return repo.strip("/")

    @staticmethod
    def get_update_page_url():
        """
        版本更新说明页地址（默认指向镜像仓库的 tag 列表）
        """
        url = str(os.environ.get("NASCINE_UPDATE_URL") or "").strip()
        if url:
            return url
        repo = WebUtils.get_image_repo()
        if "/" in repo:
            return "https://hub.docker.com/r/%s/tags" % repo
        return "https://hub.docker.com/_/%s/tags" % repo

    @staticmethod
    def __parse_version(version):
        """
        把 v2.9.1-r2 / 2.9.1 / 2.9.10 这类版本号解析成可比较的元组
        末尾修订号（-rN、.N、_N）参与比较，便于定制版持续递增
        """
        if not version:
            return None
        ver = str(version).strip().split()[0]
        match = re.match(r"^[vV]?(\d+(?:\.\d+)*)(?:[-_.]?[A-Za-z]+[._-]?(\d+)?)?$", ver)
        if not match:
            return None
        nums = [int(x) for x in match.group(1).split(".")]
        revision = int(match.group(2)) if match.group(2) else 0
        nums.append(revision)
        return tuple(nums)

    @staticmethod
    def get_current_version():
        """
        获取当前版本号
        """
        commit_id = SystemUtils.execute('git rev-parse HEAD')
        if commit_id and len(commit_id) > 7:
            commit_id = commit_id[:7]
        if commit_id:
            return "%s %s" % (APP_VERSION, commit_id)
        return APP_VERSION

    @staticmethod
    def get_latest_version():
        """
        获取最新版本号
        更新源（全部可由环境变量覆盖，无需改代码）：NASCINE_UPDATE_MODE  docker（默认）/ github / off
          NASCINE_IMAGE_REPO   镜像仓库，docker 模式据此查 Docker Hub tags
          NASCINE_UPDATE_API   自定义 JSON 接口，优先级最高
          NASCINE_UPDATE_URL   版本说明页
        """
        try:
            if WebUtils.get_update_mode() == "off":
                return None, None, False

            repo = WebUtils.get_image_repo()
            api = str(os.environ.get("NASCINE_UPDATE_API") or "").strip()
            if not api and repo:
                if WebUtils.get_update_mode() == "github":
                    api = "https://api.github.com/repos/%s/releases/latest" % repo
                else:
                    api = ("https://hub.docker.com/v2/repositories/%s/tags"
                           "?page_size=100&ordering=last_updated" % repo)
            if not api:
                return None, None, False

            res = RequestUtils(proxies=Config().get_proxies()).get_res(api)
            if not res:
                return None, None, False
            data = res.json()

            # 自定义接口：{"version": "v2.9.1-r2", "url": "..."}
            if isinstance(data, dict) and data.get("version") and not data.get("results"):
                current = WebUtils.__parse_version(APP_VERSION)
                latest = WebUtils.__parse_version(data.get("version"))
                if latest and current and latest > current:
                    return (data.get("version"),
                            data.get("url") or WebUtils.get_update_page_url(),
                            True)
                return None, None, False

            # Docker Hub tags / GitHub Release
            if isinstance(data, dict) and data.get("results"):
                candidates = [tag.get("name") for tag in data.get("results") if tag.get("name")]
            elif isinstance(data, dict) and data.get("tag_name"):
                candidates = [data.get("tag_name")]
            else:
                candidates = []

            best, best_tuple = None, None
            for name in candidates:
                parsed = WebUtils.__parse_version(name)
                if not parsed:
                    continue
                if best_tuple is None or parsed > best_tuple:
                    best, best_tuple = name, parsed

            current = WebUtils.__parse_version(APP_VERSION)
            if best and current and best_tuple > current:
                return best, WebUtils.get_update_page_url(), True
        except Exception as e:
            ExceptionUtils.exception_traceback(e)
        return None, None, False

    @staticmethod
    def get_mediainfo_from_id(mtype, mediaid):
        """
        根据TMDB/豆瓣/BANGUMI获取媒体信息
        """
        if not mediaid:
            return None
        media_info = None
        if str(mediaid).startswith("DB:"):
            # 豆瓣
            doubanid = mediaid[3:]
            info = DouBan().get_douban_detail(doubanid=doubanid, mtype=mtype)
            if not info:
                return None
            title = info.get("title")
            original_title = info.get("original_title")
            year = info.get("year")
            if original_title:
                media_info = Media().get_media_info(title=f"{original_title} {year}",
                                                    mtype=mtype,
                                                    append_to_response="all")
            if not media_info or not media_info.tmdb_info:
                media_info = Media().get_media_info(title=f"{title} {year}",
                                                    mtype=mtype,
                                                    append_to_response="all")
            media_info.douban_id = doubanid
        elif str(mediaid).startswith("BG:"):
            # BANGUMI
            bangumiid = str(mediaid)[3:]
            info = Bangumi().detail(bid=bangumiid)
            if not info:
                return None
            title = info.get("name")
            title_cn = info.get("name_cn")
            year = info.get("date")[:4] if info.get("date") else ""
            media_info = Media().get_media_info(title=f"{title} {year}",
                                                mtype=MediaType.TV,
                                                append_to_response="all")
            if not media_info or not media_info.tmdb_info:
                media_info = Media().get_media_info(title=f"{title_cn} {year}",
                                                    mtype=MediaType.TV,
                                                    append_to_response="all")
        else:
            # TMDB
            info = Media().get_tmdb_info(tmdbid=mediaid,
                                         mtype=mtype,
                                         append_to_response="all")
            if not info:
                return None
            media_info = MetaInfo(title=info.get("title") if mtype == MediaType.MOVIE else info.get("name"))
            media_info.set_tmdb_info(info)

        return media_info

    @staticmethod
    def search_media_infos(keyword, source=None, page=1):
        """
        搜索TMDB或豆瓣词条
        :param: keyword 关键字
        :param: source 渠道 tmdb/douban
        :param: season 季号
        :param: episode 集号
        """
        if not keyword:
            return []
        mtype, key_word, season_num, episode_num, _, content = StringUtils.get_keyword_from_string(keyword)
        if source == "tmdb":
            use_douban_titles = False
        elif source == "douban":
            use_douban_titles = True
        else:
            # nascine：use_douban_titles 已从设置界面移除，不再读取残留配置，默认走 TMDB
            use_douban_titles = False
        if use_douban_titles:
            medias = DouBan().search_douban_medias(keyword=key_word,
                                                   mtype=mtype,
                                                   season=season_num,
                                                   episode=episode_num,
                                                   page=page)
        else:
            meta_info = MetaInfo(title=content)
            tmdbinfos = Media().get_tmdb_infos(title=meta_info.get_name(),
                                               year=meta_info.year,
                                               mtype=mtype,
                                               page=page)
            medias = []
            for tmdbinfo in tmdbinfos:
                tmp_info = MetaInfo(title=keyword)
                tmp_info.set_tmdb_info(tmdbinfo)
                if meta_info.type != MediaType.MOVIE and tmp_info.type == MediaType.MOVIE:
                    continue
                if tmp_info.begin_season:
                    tmp_info.title = "%s 第%s季" % (tmp_info.title, cn2an.an2cn(meta_info.begin_season, mode='low'))
                if tmp_info.begin_episode:
                    tmp_info.title = "%s 第%s集" % (tmp_info.title, meta_info.begin_episode)
                medias.append(tmp_info)
        return medias
