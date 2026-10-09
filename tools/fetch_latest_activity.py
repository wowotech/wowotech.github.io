#!/usr/bin/env python3
"""从 GitHub Discussions 拉取 giscus 最新评论，刷新侧栏数据。

侧栏读 data/nav.json 的 latest_comments（前 6 条），/comments/ 页读
data/latest_comments.json（全量）。本脚本把 giscus 评论合并进这两个文件，
条目 schema 与 tools/site_data.py 生成的保持一致。

任何 API/网络失败只打警告并以 0 退出，保留现有数据——绝不能弄坏发布流水线。
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

REPO = "wowotech/wowotech.github.io"
API = "https://api.github.com/repos/" + REPO
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
FULL = os.path.join(ROOT, "data", "latest_comments.json")
NAV = os.path.join(ROOT, "data", "nav.json")
SEARCH_HEAD = os.path.join(ROOT, "assets", "search-head.json")
FULL_CAP = 400
SIDEBAR_N = 6


def api_get(url):
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "wowotech-archive-sync")
    req.add_header("Accept", "application/vnd.github+json")
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def strip_markdown(text):
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.M)
    text = re.sub(r"[*_~>]+", "", text)
    return re.sub(r"\s+", " ", text).strip()


def latest_user_comment(number):
    # 评论按创建时间升序返回，最新一条在末尾；分页取全，最多 5 页兜底
    comments = []
    for page in range(1, 6):
        batch = api_get("%s/discussions/%d/comments?per_page=100&page=%d" % (API, number, page))
        comments.extend(batch)
        if len(batch) < 100:
            break
    for c in reversed(comments):
        u = c.get("user") or {}
        login = str(u.get("login") or "")
        if u.get("type") != "Bot" and not login.endswith("[bot]"):
            return c
    return None


def build_title_map():
    with open(SEARCH_HEAD, encoding="utf-8") as f:
        entries = json.load(f)["entries"]
    m = {}
    for e in entries:
        m.setdefault(e["t"], e["u"])
    return m


def parse_date(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def collect():
    title_map = build_title_map()
    discussions = api_get(API + "/discussions?per_page=100&sort=updated&direction=desc")

    fresh = []
    for d in discussions:
        c = latest_user_comment(d["number"])
        if c is None:
            continue
        url = title_map.get(d["title"])
        if not url:
            m = re.search(r"https?://[^\s\)\]]+", d.get("body") or "")
            if m:
                url = urllib.parse.urlparse(m.group(0)).path or None
        if not url:
            continue
        text = strip_markdown(c.get("body", ""))
        if len(text) > 160:
            text = text[:160] + "…"
        fresh.append({
            "url": url,
            "author": c["user"]["login"],
            "date": c["created_at"],
            "text": text,
            "title": d["title"],
        })
    fresh.sort(key=lambda e: parse_date(e["date"]), reverse=True)
    return fresh


def write_if_changed(path, payload, **dumps_kw):
    with open(path, encoding="utf-8") as f:
        current = f.read()
    new = json.dumps(payload, ensure_ascii=False, **dumps_kw)
    if new == current:
        return False
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(new)
    return True


def main():
    fresh = collect()

    with open(FULL, encoding="utf-8") as f:
        full_list = json.load(f)
    seen = {e["url"] for e in fresh}
    merged_full = fresh + [e for e in full_list if e["url"] not in seen][:FULL_CAP - len(fresh)]

    with open(NAV, encoding="utf-8") as f:
        nav = json.load(f)
    sidebar = [dict(e, text=(e["text"][:64] + "…") if len(e["text"]) > 64 else e["text"])
               for e in merged_full[:SIDEBAR_N]]
    nav["latest_comments"] = sidebar

    # nav.json 由 site_data.py 以 indent=1 写出，序列化参数必须一致，否则每次都会假性重写
    changed_full = write_if_changed(FULL, merged_full, separators=(",", ":"))
    changed_nav = write_if_changed(NAV, nav, indent=1)

    if not changed_full and not changed_nav:
        print("giscus %d 条，侧栏数据已是最新，无需改写" % len(fresh))
        return
    print("giscus %d 条 + 归档 %d 条 → 侧栏 %d 条（已更新）" % (
        len(fresh), len(merged_full) - len(fresh), len(sidebar)))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("拉取最新评论失败（保留现有数据）：%s" % exc, file=sys.stderr)
        sys.exit(0)
