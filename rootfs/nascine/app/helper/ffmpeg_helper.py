from app.utils import SystemUtils


class FfmpegHelper:

    @staticmethod
    def get_thumb_image_from_video(video_path, image_path, frames="00:03:01"):
        """
        使用ffmpeg从视频文件中截取缩略图
        注意：必须用参数列表调用，不能拼字符串交给 shell。视频文件名来自下载的种子，
        名字里带 $(...) 或反引号时，拼进 shell 命令会被直接执行。
        """
        if not video_path or not image_path:
            return False
        cmd = ["ffmpeg", "-i", video_path, "-ss", frames,
               "-vframes", "1", "-f", "image2", image_path]
        result = SystemUtils.execute(cmd)
        if result:
            return True
        return False
