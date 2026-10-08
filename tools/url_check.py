"""校验 emlog 的 URL 规则并输出清单，供迁移时保持外链。

emlog 5.x 的伪静态规则推测为 /{分类alias}/{alias 或 gid}.html，页面为 /{alias}.html。
本脚本对真实线上地址发请求，用标题是否命中来判断规则，避免猜错导致外链失效。
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import sqldump  # noqa: E402

UA = {"User-Agent": "Mozilla/5.0 (compatible; wowotech-migration/1.0)"}


def fetch(url: str, timeout: int = 25) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
            raw = r.read()
            return r.status, raw.decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:  # 网络异常
        return -1, str(e)


def title_of(html: str) -> str:
    m = re.search(r"<title>(.*?)</title>", html, re.S)
    return m.group(1).strip() if m else ""


def main():
    base = "http://www.wowotech.net"
    posts = sqldump.records("recon/emlog_20250207.sql", "emlog_blog")
    sorts = {r["sid"]: r["alias"] for r in sqldump.records("recon/emlog_20250207.sql", "emlog_sort")}

    with_alias = [p for p in posts if (p["alias"] or "").strip() and p["type"] == "blog"]
    no_alias = [p for p in posts if not (p["alias"] or "").strip() and p["type"] == "blog"]
    pages = [p for p in posts if p["type"] == "page"]

    out = []
    out.append(f"文章总数 {len(posts)}：有 alias {len(with_alias)}，无 alias {len(no_alias)}，页面 {len(pages)}")
    out.append(f"sortid 无对应分类的文章: {sum(1 for p in posts if p['sortid'] not in sorts and p['type']=='blog')}")

    cases = []
    for p in with_alias[:3]:
        cases.append((p, f"{base}/{sorts.get(p['sortid'],'')}/{p['alias']}.html", "有alias→alias"))
        cases.append((p, f"{base}/{sorts.get(p['sortid'],'')}/{p['gid']}.html", "有alias→gid(应失效)"))
    for p in no_alias[:4]:
        cases.append((p, f"{base}/{sorts.get(p['sortid'],'')}/{p['gid']}.html", "无alias→gid"))
    for p in pages[:3]:
        cases.append((p, f"{base}/{p['alias']}.html", "页面→根路径"))
    cases.append((posts[0], f"{base}/?post={posts[0]['gid']}", "动态形式"))

    out.append("\n=== 实测 ===")
    for p, url, label in cases:
        status, html = fetch(url)
        t = title_of(html)
        hit = "命中" if p["title"][:12] in t else ("同名类" if t else "")
        out.append(f"[{status:>3}] {label:22s} {url}\n        标题={t[:60]} {hit}")

    Path("recon/url_check.txt").write_text("\n".join(out), encoding="utf-8")
    print("written recon/url_check.txt")


if __name__ == "__main__":
    main()
