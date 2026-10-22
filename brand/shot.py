#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用 Chrome DevTools Protocol 截取 nascine 界面（登录 → 主页 → 深色）。"""

import base64
import json
import os
import subprocess
import sys
import time
import urllib.request

import websocket

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PORT = 9333
BASE = "http://127.0.0.1:3000"
OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "shots")


class CDP:
    def __init__(self, url):
        self.ws = websocket.create_connection(url, timeout=30,
                                             max_size=64 * 1024 * 1024)
        self.seq = 0

    def send(self, method, **params):
        self.seq += 1
        self.ws.send(json.dumps({"id": self.seq, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self.seq:
                if "error" in msg:
                    raise RuntimeError("%s -> %s" % (method, msg["error"]))
                return msg.get("result", {})

    def eval(self, expr, await_promise=False):
        r = self.send("Runtime.evaluate", expression=expr, returnByValue=True,
                      awaitPromise=await_promise, userGesture=True)
        return r.get("result", {}).get("value")

    def shot(self, path, clip=None, full=False):
        params = {"format": "png", "captureBeyondViewport": full}
        if clip:
            params["clip"] = dict(clip, scale=2)
        else:
            params["clip"] = {"x": 0, "y": 0, "width": 1440, "height": 900, "scale": 1}
        data = self.send("Page.captureScreenshot", **params)["data"]
        with open(path, "wb") as f:
            f.write(base64.b64decode(data))
        print("  ->", path)


def start_chrome():
    subprocess.run(["pkill", "-f", "nascine-shot-chrome"], capture_output=True)
    subprocess.run(["rm", "-rf", "/tmp/nascine-shot-chrome"], capture_output=True)
    time.sleep(0.5)
    subprocess.run(["rm", "-rf", "/tmp/nascine-shot-chrome"], capture_output=True)
    time.sleep(0.5)
    args = [CHROME, "--headless=new", "--no-sandbox", "--disable-gpu",
            "--hide-scrollbars", "--remote-debugging-port=%d" % PORT,
            "--remote-allow-origins=*",
            "--remote-allow-origins=*",
            "--user-data-dir=/tmp/nascine-shot-chrome",
            "--window-size=1440,900", "--force-device-scale-factor=1",
            "about:blank"]
    proc = subprocess.Popen(args, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    for _ in range(60):
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/json/list" % PORT,
                                        timeout=1) as r:
                tabs = json.load(r)
            for t in tabs:
                if t.get("type") == "page":
                    return proc, t["webSocketDebuggerUrl"]
        except Exception:
            pass
        time.sleep(0.3)
    raise RuntimeError("Chrome 未就绪")


def main():
    os.makedirs(OUT, exist_ok=True)
    proc, ws_url = start_chrome()
    c = CDP(ws_url)
    c.send("Page.enable")
    c.send("Runtime.enable")
    c.send("Emulation.setDeviceMetricsOverride", width=1440, height=900,
           deviceScaleFactor=1, mobile=False)

    def goto(url):
        c.send("Page.navigate", url=url)
        time.sleep(2.2)

    # 1. 登录页
    goto(BASE + "/")
    print("login title:", c.eval("document.title"))
    c.shot(os.path.join(OUT, "01-login.png"))

    # 2. 登录
    c.eval("""
      document.querySelector('input[name=username]').value='admin';
      document.querySelector('input[name=password]').value='password';
      document.querySelector('form').submit(); 'ok'
    """)
    time.sleep(4)

    # 3. 关掉「未配置 API Key」弹窗
    c.eval("document.querySelector('.modal.show .btn')?.click();"
           "document.querySelectorAll('.modal-backdrop').forEach(e=>e.remove());"
           "document.body.classList.remove('modal-open'); 'ok'")
    time.sleep(0.8)

    # 4. 主页（先切到 index，避免被引导到基础设置）
    c.eval("navmenu('index')")
    time.sleep(3)
    print("after login title:", c.eval("document.title"))
    c.shot(os.path.join(OUT, "02-index-light.png"))

    # 4. 侧栏品牌特写
    box = c.eval("""
      (() => {const r=document.querySelector('.ap-brand').getBoundingClientRect();
      return JSON.stringify({x:r.x,y:r.y,width:r.width,height:r.height});})()
    """)
    if box:
        b = json.loads(box)
        c.shot(os.path.join(OUT, "03-brand.png"),
               clip={"x": b["x"], "y": b["y"], "width": b["width"], "height": b["height"]})

    # 5. 深色模式
    c.eval("document.body.classList.remove('theme-light');"
           "document.body.classList.add('theme-dark')")
    time.sleep(1.2)
    c.shot(os.path.join(OUT, "04-index-dark.png"))

    # 6. 设置页（浅色）
    c.eval("document.body.classList.remove('theme-dark');"
           "document.body.classList.add('theme-light');")
    c.eval("navmenu('setting?tab=basic')")
    time.sleep(2.5)
    c.shot(os.path.join(OUT, "05-setting.png"))

    # 7. 图标与 manifest 自检
    print("manifest:", c.eval("fetch('../static/site.webmanifest').then(r=>r.text()).then(t=>t.slice(0,80))", True))
    print("favicon:", c.eval("fetch('../static/favicon.ico').then(r=>r.status)"))
    proc.terminate()


if __name__ == "__main__":
    main()
