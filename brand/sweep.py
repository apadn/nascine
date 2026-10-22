#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""逐页点开 nascine 的所有导航项，抓取渲染文本，检查是否还有旧品牌残留。"""

import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shot as S  # noqa

BAD = re.compile(r"nas[-_ ]?tools?", re.I)


def main():
    out = os.path.abspath(sys.argv[1])
    os.makedirs(out, exist_ok=True)
    proc, url = S.start_chrome()
    c = S.CDP(url)
    c.send("Page.enable")
    c.send("Runtime.enable")
    c.send("Emulation.setDeviceMetricsOverride", width=1440, height=900,
           deviceScaleFactor=1, mobile=False)
    c.send("Page.navigate", url="http://127.0.0.1:3000/")
    time.sleep(2.5)
    c.eval("document.querySelector('input[name=username]').value='admin';"
           "document.querySelector('input[name=password]').value='password';"
           "document.querySelector('form').submit();'ok'")
    time.sleep(4.5)
    c.eval("document.querySelector('.modal.show .btn')?.click();"
           "document.querySelectorAll('.modal-backdrop').forEach(e=>e.remove());"
           "document.body.classList.remove('modal-open');'ok'")
    time.sleep(0.6)

    names = json.loads(c.eval(
        "JSON.stringify([...document.querySelectorAll('.ap-item')].map(e=>e.textContent.trim()))"))
    findings = []
    for idx, name in enumerate(names):
        clicked = c.eval(
            "(()=>{const el=[...document.querySelectorAll('.ap-item')]"
            ".find(e=>e.textContent.trim()==='%s'); if(!el) return 'no';"
            "el.click(); return 'ok';})()" % name.replace("'", "\\'"))
        if clicked != "ok":
            continue
        time.sleep(2.2)
        text = c.eval("document.querySelector('#page_content')?.innerText || ''") or ""
        title = c.eval("document.title") or ""
        hits = BAD.findall(text) + BAD.findall(title)
        tag = "OK " if not hits else "BAD"
        print("%s %-8s %s" % (tag, name, (title or "")[:40]))
        if hits:
            findings.append((name, set(hits)))
            for line in text.splitlines():
                if BAD.search(line):
                    print("      !", line.strip()[:120])
        c.shot(os.path.join(out, "%02d-%s.png" % (idx + 1, name.replace("/", "-"))))

    print("\n=== 结果 ===")
    if findings:
        for name, hits in findings:
            print("残留：%s -> %s" % (name, hits))
    else:
        print("所有页面均无 NAS-Tools 残留")
    proc.terminate()


if __name__ == "__main__":
    main()
