import datetime
from functools import wraps

import jwt
from flask import request, has_request_context, abort, g
from flask_login import current_user

from app.utils import TokenCache
from config import Config

# 受限用户（非管理员）允许调用的动作：查询浏览、下载、订阅
# 未列出的动作一律按管理员处理，新增动作时默认就是"仅管理员"，避免再漏掉鉴权
USER_ACTIONS = frozenset({
    # 查询 / 浏览
    "sch", "search", "logging", "version", "logout", "get_site_favicon",
    "media_info", "media_detail", "media_similar", "media_recommendations",
    "media_person", "person_medias", "get_search_result", "search_media_infos",
    "get_recommend", "get_library_mediacount", "get_library_spacesize",
    "get_library_playhistory", "get_transfer_statistics", "get_transfer_history",
    "get_unknown_list", "get_categories", "get_tvseason_list", "get_sub_path",
    "get_downloaded", "get_downloading", "get_downloader", "get_download_setting",
    "pt_info", "find_hardlinks", "get_movie_rss_list", "get_tv_rss_list",
    "get_rss_history", "rss_detail", "list_rss_articles", "list_rss_history",
    "list_site_resources", "get_userrss_task", "get_rssparser", "get_filterrules",
    "filterrule_detail", "get_customwords", "get_custom_word", "get_directorysync",
    "get_users", "get_sites", "get_indexers", "get_download_dirs",
    "get_message_client", "get_torrent_remove_task", "get_remove_torrents",
    "get_douban_history", "get_site_user_statistics", "get_site_activity",
    "get_site_history", "mediasync_state", "brushtask_detail",
    "list_brushtask_torrents", "movie_calendar_data", "tv_calendar_data",
    # 下载 / 订阅
    "download", "download_link", "download_torrent", "download_subtitle",
    "pt_start", "pt_stop", "pt_remove",
    "add_rss_media", "remove_rss_media", "update_userrss_task",
    "delete_userrss_task", "run_userrss",
    "delete_history", "re_identification",
})

# 这些前缀的动作都是只读查询
USER_ACTION_PREFIXES = ("get_", "list_")


def is_admin_user(user):
    """
    是否管理员：配置文件里的主账号，或权限里包含「系统设置」的用户
    """
    if not user or not getattr(user, "is_authenticated", False):
        return False
    # 配置文件里的主账号固定 id 为 0
    if str(getattr(user, "id", "")) == "0":
        return True
    app_conf = Config().get_config("app") or {}
    login_user = app_conf.get("login_user")
    if login_user and getattr(user, "username", None) == login_user:
        return True
    return "系统设置" in str(getattr(user, "pris", "") or "")


def check_action_permission(cmd, user=None):
    """
    动作级权限校验，返回 None 表示放行，否则返回错误响应
    - 没有请求上下文（定时任务、消息渠道内部调用）：放行
    - ApiKey 认证（current_user 为匿名）：放行，ApiKey 本身就是管理员凭据
    - 受限用户：只放行只读查询和下载订阅类动作
    """
    if not cmd:
        return None
    if not has_request_context():
        return None
    if cmd in USER_ACTIONS or str(cmd).startswith(USER_ACTION_PREFIXES):
        return None
    if user is None:
        user = current_user
        if not getattr(user, "is_authenticated", False):
            # api 通道（Authorization: JWT）没有 session，用 login_required 记下的用户名
            api_username = getattr(g, "api_username", None)
            if api_username:
                from web.backend.user import User as WebUser
                user = WebUser().get_user(api_username)
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    if is_admin_user(user):
        return None
    return {"code": -1, "msg": "当前用户没有执行该操作的权限"}


def admin_required(func):
    """
    页面级管理员校验：受限用户（只有「我的媒体库」等权限）不能打开系统设置类页面
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        if not is_admin_user(current_user):
            abort(403)
        return func(*args, **kwargs)

    return wrapper


def require_auth(func):
    """
    API安全认证
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization")
        if auth:
            auth = str(auth).split()[-1]
            if auth == Config().get_config("security").get("api_key"):
                return func(*args, **kwargs)
        return {
            "code": 401,
            "success": False,
            "message": "安全认证未通过，请检查ApiKey"
        }

    return wrapper


def generate_access_token(username: str, algorithm: str = 'HS256', exp: float = 2):
    """
    生成access_token
    :param username: 用户名(自定义部分)
    :param algorithm: 加密算法
    :param exp: 过期时间，默认2小时
    :return:token
    """

    now = datetime.datetime.utcnow()
    exp_datetime = now + datetime.timedelta(hours=exp)
    access_payload = {
        'exp': exp_datetime,
        'iat': now,
        'username': username
    }
    access_token = jwt.encode(access_payload,
                              Config().get_config("security").get("api_key"),
                              algorithm=algorithm)
    return access_token


def __decode_auth_token(token: str, algorithms='HS256'):
    """
    解密token
    :param token:token字符串
    :return: 是否有效，playload
    """
    key = Config().get_config("security").get("api_key")
    try:
        payload = jwt.decode(token,
                             key=key,
                             algorithms=algorithms)
    except jwt.ExpiredSignatureError:
        return False, jwt.decode(token,
                                 key=key,
                                 algorithms=algorithms,
                                 options={'verify_exp': False})
    except (jwt.DecodeError, jwt.InvalidTokenError, jwt.ImmatureSignatureError):
        return False, {}
    else:
        return True, payload


def identify(auth_header: str):
    """
    用户鉴权，返回是否有效、用户名
    """
    flag = False
    if auth_header:
        flag, payload = __decode_auth_token(auth_header)
        if payload:
            return flag, payload.get("username") or ""
    return flag, ""


def login_required(func):
    """
    登录保护，验证用户是否登录
    :param func:
    :return:
    """

    @wraps(func)
    def wrapper(*args, **kwargs):

        def auth_failed():
            return {
                "code": 403,
                "success": False,
                "message": "安全认证未通过，请检查Token"
            }

        token = request.headers.get("Authorization", default=None)
        if not token:
            return auth_failed()
        latest_token = TokenCache.get(token)
        if not latest_token:
            return auth_failed()
        flag, username = identify(latest_token)
        if not username:
            return auth_failed()
        # 记下 JWT 的真实用户，动作级权限校验要用（api 通道没有 session/current_user）
        g.api_username = username
        if not flag and username:
            TokenCache.set(token, generate_access_token(username))
        return func(*args, **kwargs)

    return wrapper
