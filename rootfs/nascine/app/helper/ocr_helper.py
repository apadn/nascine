import base64
import os

from app.utils import RequestUtils


class OcrHelper:
    """
    验证码识别（可选能力）

    本项目不内置任何第三方 OCR 服务地址。只有自行部署了 OCR 服务、并把地址
    写进环境变量 NASCINE_OCR_SERVER 时才会启用；未配置时一律返回空字符串，
    调用方按「未识别出验证码」处理，不会发起任何外部请求。
    """

    req = None
    _ocr_b64_url = None

    def __init__(self):
        self.req = RequestUtils(content_type="application/json")
        server = (os.environ.get("NASCINE_OCR_SERVER") or "").strip().rstrip("/")
        self._ocr_b64_url = "%s/captcha/base64" % server if server else None

    def get_captcha_text(self, image_url=None, image_b64=None):
        """
        根据图片地址，获取验证码图片，并识别内容
        """
        if not self._ocr_b64_url:
            return ""
        if not image_url and not image_b64:
            return ""
        if image_url:
            ret = self.req.get_res(image_url)
            if ret is not None:
                image_bin = ret.content
                if not image_bin:
                    return ""
                image_b64 = base64.b64encode(image_bin).decode()
        ret = self.req.post_res(url=self._ocr_b64_url,
                                json={"base64_img": image_b64})
        if ret:
            return ret.json().get("result")
        return ""
