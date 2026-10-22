import os
import threading
import time
import traceback

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver

import log
from app.conf import ModuleConf
from app.helper import DbHelper
from config import RMT_MEDIAEXT, Config
from app.filetransfer import FileTransfer
from app.utils.commons import singleton
from app.utils import PathUtils, ExceptionUtils
from app.utils.types import RmtMode, SyncType, OsType

lock = threading.Lock()


def get_fs_type(path):
    """
    返回指定路径所在挂载点的文件系统类型，取不到时返回空字符串
    用于识别 Unraid 的 /mnt/user（fuse.shfs）等不支持可靠 inotify 的挂载
    :param path: 目录路径
    """
    try:
        path = os.path.abspath(path)
        best_mount = ""
        best_type = ""
        with open("/proc/mounts", "r") as f:
            for line in f:
                parts = line.split()
                if len(parts) < 3:
                    continue
                mount_point = parts[1].replace("\\040", " ")
                if path == mount_point or path.startswith(mount_point.rstrip("/") + "/"):
                    if len(mount_point) >= len(best_mount):
                        best_mount = mount_point
                        best_type = parts[2]
        return best_type
    except Exception:
        return ""


def is_fuse_path(path):
    """
    判断路径是否位于 FUSE 类文件系统（Unraid 的 /mnt/user 为 fuse.shfs）
    FUSE 挂载下的 inotify 事件在跨容器场景下不可靠，需要降级为轮询
    """
    fs_type = get_fs_type(path)
    return fs_type.startswith("fuse")


class FileMonitorHandler(FileSystemEventHandler):
    """
    目录监控响应类
    """

    def __init__(self, monpath, sync, **kwargs):
        super(FileMonitorHandler, self).__init__(**kwargs)
        self._watch_path = monpath
        self.sync = sync

    def on_created(self, event):
        self.sync.file_change_handler(event, "创建", event.src_path)

    def on_moved(self, event):
        self.sync.file_change_handler(event, "移动", event.dest_path)

    """
    def on_modified(self, event):
        self.sync.file_change_handler(event, "修改", event.src_path)
    """


@singleton
class Sync(object):
    filetransfer = None
    dbhelper = None

    sync_dir_config = {}
    _observer = []
    _sync_paths = []
    _sync_sys = OsType.LINUX
    # 已处理过的文件，key 为 inode+大小+修改时间。
    # 用 inode 而不是路径，是因为文件被"原地改名"后路径变了但 inode 不变，
    # 用路径判断会把同一个文件当成新文件重复转移（重复转移会覆盖掉正常文件）
    _synced_files = {}
    _synced_files_max = 5000
    _need_sync_paths = {}
    # 转移失败后的最大重试次数（应对下载器仍在校验/文件仍在写入等临时性失败）
    _max_retry = 3

    def __init__(self):
        self.init_config()

    def init_config(self):
        self.dbhelper = DbHelper()
        self.filetransfer = FileTransfer()
        sync = Config().get_config('sync')
        sync_paths = self.dbhelper.get_config_sync_paths()
        if sync and sync_paths:
            if sync.get('nas_sys') == "windows":
                self._sync_sys = OsType.WINDOWS
            self._sync_paths = sync_paths
            self.init_sync_dirs()

    def init_sync_dirs(self):
        """
        初始化监控文件配置
        """
        self.sync_dir_config = {}
        if self._sync_paths:
            for sync_item in self._sync_paths:
                if not sync_item:
                    continue
                # ID
                sync_id = sync_item.ID
                # 启用标志
                enabled = True if sync_item.ENABLED else False
                # 仅硬链接标志
                only_link = False if sync_item.RENAME else True
                # 转移方式
                path_syncmode = ModuleConf.RMT_MODES_SIMPLE.get(sync_item.MODE, RmtMode.COPY)
                # 源目录|目的目录|未知目录
                monpath = sync_item.SOURCE
                target_path = sync_item.DEST
                unknown_path = sync_item.UNKNOWN
                if target_path and unknown_path:
                    log.info("【Sync】读取到监控目录：%s，目的目录：%s，未识别目录：%s，转移方式：%s" % (
                        monpath, target_path, unknown_path, path_syncmode.value))
                elif target_path:
                    log.info(
                        "【Sync】读取到监控目录：%s，目的目录：%s，转移方式：%s" % (monpath, target_path, path_syncmode.value))
                else:
                    log.info("【Sync】读取到监控目录：%s，转移方式：%s" % (monpath, path_syncmode.value))
                if not enabled:
                    log.info("【Sync】%s 不进行监控和同步：手动关闭" % monpath)
                    continue
                if only_link:
                    log.info("【Sync】%s 不进行识别和重命名" % monpath)
                if target_path and not os.path.exists(target_path):
                    log.info("【Sync】目的目录不存在，正在创建：%s" % target_path)
                    os.makedirs(target_path)
                if unknown_path and not os.path.exists(unknown_path):
                    log.info("【Sync】未识别目录不存在，正在创建：%s" % unknown_path)
                    os.makedirs(unknown_path)
                # 登记关系
                if os.path.exists(monpath):
                    # 统一成 normpath 作为 key：同一个目录配置了多次（比如之前
                    # 报错时重复添加）时只会挂一个 watch，否则同一个文件会收到
                    # 多次事件，被并发转移两次
                    mon_key = os.path.normpath(monpath)
                    if mon_key in self.sync_dir_config:
                        log.warn("【Sync】%s 重复配置，已忽略（目的目录：%s），"
                                 "建议在目录同步页面删除多余记录" % (monpath, target_path))
                        continue
                    self.sync_dir_config[mon_key] = {
                        'id': sync_id,
                        'target': target_path,
                        'unknown': unknown_path,
                        'onlylink': only_link,
                        'syncmod': path_syncmode
                    }
                else:
                    log.error("【Sync】%s 目录不存在！" % monpath)

    def get_sync_dirs(self):
        """
        返回所有的同步监控目录
        """
        if not self.sync_dir_config:
            return []
        return [os.path.normpath(key) for key in self.sync_dir_config.keys()]

    @staticmethod
    def get_file_key(path):
        """
        计算文件的唯一标识：inode + 大小 + 修改时间
        文件在同一目录内改名后 inode/大小/修改时间都不变，用这个 key 可以识别出
        "还是同一个文件"，避免被当成新文件重复转移；取不到 stat 时退回路径
        :param path: 文件路径
        """
        try:
            st = os.stat(path)
            return "%s:%s:%s:%s" % (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns)
        except OSError:
            return "path:%s" % os.path.normpath(path)

    def file_change_handler(self, event, text, event_path):
        """
        处理文件变化
        :param event: 事件
        :param text: 事件描述
        :param event_path: 事件文件路径
        """
        if not event.is_directory:
            # 文件发生变化
            try:
                if not os.path.exists(event_path):
                    return
                log.debug("【Sync】文件%s：%s" % (text, event_path))
                # 判断是否处理过了
                need_handler_flag = False
                file_key = self.get_file_key(event_path)
                try:
                    lock.acquire()
                    if file_key not in self._synced_files:
                        self._synced_files[file_key] = time.time()
                        need_handler_flag = True
                    # 记录过多时清掉最早的一半，避免长期运行后内存无限增长
                    if len(self._synced_files) > self._synced_files_max:
                        for _key in sorted(self._synced_files,
                                           key=self._synced_files.get)[:self._synced_files_max // 2]:
                            self._synced_files.pop(_key, None)
                finally:
                    lock.release()
                if not need_handler_flag:
                    log.debug("【Sync】文件已处理过：%s" % event_path)
                    return
                # 不是监控目录下的文件不处理
                is_monitor_file = False
                for tpath in self.sync_dir_config.keys():
                    if PathUtils.is_path_in_path(tpath, event_path):
                        is_monitor_file = True
                        break
                if not is_monitor_file:
                    return
                # 目的目录的子文件不处理
                for tpath in self.sync_dir_config.values():
                    if not tpath:
                        continue
                    if PathUtils.is_path_in_path(tpath.get('target'), event_path):
                        return
                    if PathUtils.is_path_in_path(tpath.get('unknown'), event_path):
                        return
                # 媒体库目录及子目录不处理
                if self.filetransfer.is_target_dir_path(event_path):
                    return
                # 回收站及隐藏的文件不处理
                if PathUtils.is_invalid_path(event_path):
                    return
                # 上级目录
                from_dir = os.path.dirname(event_path)
                # 找到是哪个监控目录下的
                monitor_dir = event_path
                is_root_path = False
                for m_path in self.sync_dir_config.keys():
                    if PathUtils.is_path_in_path(m_path, event_path):
                        monitor_dir = m_path
                    if os.path.normpath(m_path) == os.path.normpath(from_dir):
                        is_root_path = True

                # 查找目的目录
                target_dirs = self.sync_dir_config.get(monitor_dir)
                target_path = target_dirs.get('target')
                unknown_path = target_dirs.get('unknown')
                onlylink = target_dirs.get('onlylink')
                sync_mode = target_dirs.get('syncmod')

                # 只做硬链接，不做识别重命名
                if onlylink:
                    if self.dbhelper.is_sync_in_history(event_path, target_path):
                        return
                    log.info("【Sync】开始同步 %s" % event_path)
                    ret, msg = self.filetransfer.link_sync_file(src_path=monitor_dir,
                                                                in_file=event_path,
                                                                target_dir=target_path,
                                                                sync_transfer_mode=sync_mode)
                    if ret != 0:
                        log.warn("【Sync】%s 同步失败，错误码：%s" % (event_path, ret))
                    elif not msg:
                        self.dbhelper.insert_sync_history(event_path, monitor_dir, target_path)
                        log.info("【Sync】%s 同步完成" % event_path)
                # 识别转移
                else:
                    # 不是媒体文件不处理
                    name = os.path.basename(event_path)
                    if not name:
                        return
                    if name.lower() != "index.bdmv":
                        ext = os.path.splitext(name)[-1]
                        if ext.lower() not in RMT_MEDIAEXT:
                            return
                    # 监控根目录下的文件发生变化时直接发走
                    if is_root_path:
                        ret, ret_msg = self.filetransfer.transfer_media(in_from=SyncType.MON,
                                                                        in_path=event_path,
                                                                        target_dir=target_path,
                                                                        unknown_dir=unknown_path,
                                                                        rmt_mode=sync_mode)
                        if not ret:
                            log.warn("【Sync】%s 转移失败：%s" % (event_path, ret_msg))
                    else:
                        try:
                            lock.acquire()
                            if self._need_sync_paths.get(from_dir):
                                files = self._need_sync_paths[from_dir].get('files')
                                if not files:
                                    files = [event_path]
                                else:
                                    if event_path not in files:
                                        files.append(event_path)
                                    else:
                                        return
                                self._need_sync_paths[from_dir].update({'files': files})
                            else:
                                self._need_sync_paths[from_dir] = {'target': target_path,
                                                                   'unknown': unknown_path,
                                                                   'syncmod': sync_mode,
                                                                   'files': [event_path]}
                        finally:
                            lock.release()
            except Exception as e:
                ExceptionUtils.exception_traceback(e)
                log.error("【Sync】发生错误：%s - %s" % (str(e), traceback.format_exc()))

    def transfer_mon_files(self):
        """
        批量转移文件，由定时服务定期调用执行
        """
        try:
            lock.acquire()
            finished_paths = []
            for path in list(self._need_sync_paths):
                # 文件已消失（被移走或删除）则直接出队，避免队列长期堆积
                if PathUtils.is_invalid_path(path) or not os.path.exists(path):
                    self._need_sync_paths.pop(path, None)
                    continue
                target_info = self._need_sync_paths.get(path) or {}
                # 失败后按退避时间重试，未到时间则跳过
                if target_info.get('next_at', 0) > time.time():
                    continue
                log.info("【Sync】开始转移监控目录文件...")
                bluray_dir = PathUtils.get_bluray_dir(path)
                if not bluray_dir:
                    src_path = path
                    files = target_info.get('files')
                else:
                    src_path = bluray_dir
                    files = []
                if src_path in finished_paths:
                    self._need_sync_paths.pop(path, None)
                    continue
                finished_paths.append(src_path)
                target_path = target_info.get('target')
                unknown_path = target_info.get('unknown')
                sync_mode = target_info.get('syncmod')
                # 判断是否根目录
                is_root_path = False
                for m_path in self.sync_dir_config.keys():
                    if os.path.normpath(m_path) == os.path.normpath(src_path):
                        is_root_path = True
                ret, ret_msg = self.filetransfer.transfer_media(in_from=SyncType.MON,
                                                                in_path=src_path,
                                                                files=files,
                                                                target_dir=target_path,
                                                                unknown_dir=unknown_path,
                                                                rmt_mode=sync_mode,
                                                                root_path=is_root_path)
                if not ret:
                    attempts = int(target_info.get('attempts') or 0) + 1
                    if attempts < self._max_retry and os.path.exists(path):
                        target_info['attempts'] = attempts
                        target_info['next_at'] = time.time() + 60 * attempts
                        self._need_sync_paths[path] = target_info
                        log.warn("【Sync】%s转移失败（第%s次，%s秒后重试）：%s" % (
                            path, attempts, 60 * attempts, ret_msg))
                        continue
                    log.warn("【Sync】%s转移失败，已放弃：%s" % (path, ret_msg))
                self._need_sync_paths.pop(path, None)
        finally:
            lock.release()

    def run_service(self):
        """
        启动监控服务
        """
        self._observer = []
        try:
            log.info("【Sync】运行身份 uid=%s gid=%s，监控目录系统类型=%s" % (
                os.getuid(), os.getgid(), self._sync_sys))
        except Exception:
            pass
        for monpath in self.sync_dir_config.keys():
            if monpath and os.path.exists(monpath):
                try:
                    fs_type = get_fs_type(monpath)
                    # Windows 模式或 FUSE 挂载（如 Unraid 的 /mnt/user）下 inotify 不可靠，
                    # 改用轮询，避免其它容器写入后收不到事件导致不自动转移
                    use_polling = self._sync_sys == OsType.WINDOWS or is_fuse_path(monpath)
                    if use_polling:
                        observer = PollingObserver(timeout=10)
                        log.info("【Sync】%s（%s）使用轮询监控" % (monpath, fs_type or "未知文件系统"))
                    else:
                        observer = Observer(timeout=10)
                        log.info("【Sync】%s（%s）使用事件监控" % (monpath, fs_type or "未知文件系统"))
                    self._observer.append(observer)
                    observer.schedule(FileMonitorHandler(monpath, self), path=monpath, recursive=True)
                    observer.daemon = True
                    observer.start()
                    log.info("%s 的监控服务启动" % monpath)
                except Exception as e:
                    ExceptionUtils.exception_traceback(e)
                    log.error("%s 启动目录监控失败：%s" % (monpath, str(e)))

    def stop_service(self):
        """
        关闭监控服务
        """
        if self._observer:
            for observer in self._observer:
                observer.stop()
        self._observer = []

    def transfer_all_sync(self, sid=None):
        """
        全量转移Sync目录下的文件，WEB界面点击目录同步时获发
        """
        for monpath, target_dirs in self.sync_dir_config.items():
            if not monpath:
                continue
            if sid and sid != target_dirs.get('id'):
                continue
            target_path = target_dirs.get('target')
            unknown_path = target_dirs.get('unknown')
            onlylink = target_dirs.get('onlylink')
            sync_mode = target_dirs.get('syncmod')
            # 只做硬链接，不做识别重命名
            if onlylink:
                for link_file in PathUtils.get_dir_files(monpath):
                    if self.dbhelper.is_sync_in_history(link_file, target_path):
                        continue
                    log.info("【Sync】开始同步 %s" % link_file)
                    ret, msg = self.filetransfer.link_sync_file(src_path=monpath,
                                                                in_file=link_file,
                                                                target_dir=target_path,
                                                                sync_transfer_mode=sync_mode)
                    if ret != 0:
                        log.warn("【Sync】%s 同步失败，错误码：%s" % (link_file, ret))
                    elif not msg:
                        self.dbhelper.insert_sync_history(link_file, monpath, target_path)
                        log.info("【Sync】%s 同步完成" % link_file)
            else:
                for path in PathUtils.get_dir_level1_medias(monpath, RMT_MEDIAEXT):
                    if PathUtils.is_invalid_path(path):
                        continue
                    ret, ret_msg = self.filetransfer.transfer_media(in_from=SyncType.MON,
                                                                    in_path=path,
                                                                    target_dir=target_path,
                                                                    unknown_dir=unknown_path,
                                                                    rmt_mode=sync_mode)
                    if not ret:
                        log.error("【Sync】%s 处理失败：%s" % (monpath, ret_msg))


def run_monitor():
    """
    启动监控
    """
    try:
        Sync().run_service()
    except Exception as err:
        ExceptionUtils.exception_traceback(err)
        log.error("启动目录同步服务失败：%s" % str(err))


def stop_monitor():
    """
    停止监控
    """
    try:
        Sync().stop_service()
    except Exception as err:
        ExceptionUtils.exception_traceback(err)
        log.error("停止目录同步服务失败：%s" % str(err))


def restart_monitor():
    """
    重启监控
    """
    stop_monitor()
    run_monitor()
