"""生成侧栏与站内搜索需要的数据与页面。

原站侧栏有六个模块（站内搜索、功能、最新评论、文章分类、随机文章、文章存档），
静态站要把它们变成「构建时算好的数据 + 少量 JS」。这个模块负责数据那部分：

  data/nav.json               分类、存档（按年→月）、友情链接、站点统计
  data/latest_comments.json   最新评论（侧栏与 /comments/ 用）
  data/random.json            随机文章的候选地址（/random/ 页用）
  static/search-index.json    全文搜索索引（标题、分类、标签、正文纯文本）
  content/_gen/comments.md    /comments/ 全站评论列表页
  content/_gen/random.md      /random/ 「随便看看」跳转页
  content/_gen/nav.md         /nav/ 站内导航总览页
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))


def iso_date(ts) -> str:
    """kept 里存的是数据库原始时间戳，这里换算成 ISO 日期（与 front matter 一致）。"""
    try:
        return datetime.fromtimestamp(int(ts), CST).isoformat()
    except (TypeError, ValueError):
        return ""


def plain_text(text: str) -> str:
    """把 Markdown／HTML 压成用于检索与摘要的纯文本。"""
    t = re.sub(r"```.*?```", " ", text, flags=re.S)
    t = re.sub(r"<script.*?</script>", " ", t, flags=re.S | re.I)
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", t)              # 图片
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)            # 链接留文字
    t = re.sub(r"<[^>]+>", " ", t)                            # 残留 HTML
    t = re.sub(r"[*_~`]+", "", t)                             # 强调符号
    t = re.sub(r"^\s*[-#>]+\s*", "", t, flags=re.M)           # 行首标记
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def read_corpus(root: Path) -> list[dict]:
    """读回已生成的 Markdown 语料，取出检索需要的最小字段。"""
    items = []
    for f in sorted((root / "content").rglob("*.md")):
        if "_gen" in f.parts:            # 生成页只是导航，不进检索
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        if not text.startswith("---"):
            continue
        parts = text.split("---", 2)
        if len(parts) < 3:
            continue
        fm, body = parts[1], parts[2]
        meta = {}
        for line in fm.strip().splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip().strip('"')
        url = meta.get("url")
        if not url:
            continue
        tags = re.findall(r'"([^"]+)"', meta.get("tags", ""))
        items.append({
            "url": url,
            "title": meta.get("title", f.stem),
            "date": meta.get("date", "")[:10],
            "category": meta.get("category", ""),
            "tags": tags,
            "text": plain_text(body),
        })
    return items


def write_nav_data(root: Path, kept: list[dict], comments: dict, sorts: dict,
                   gid2url: dict, forum_topics: int,
                   forum_posts: int, report: list[str]) -> None:
    data = root / "data"
    data.mkdir(parents=True, exist_ok=True)

    # ---- 分类两级树：emlog_sort 用 pid 表达层级（如「统一设备模型」挂在
    #      「Linux内核分析」下）。count 只算直挂的文章，与原站侧栏一致 ----
    counts: dict[str, int] = {}
    for p in kept:
        s = sorts.get(p["sortid"])
        if s and p["type"] != "page":
            counts[s["sid"]] = counts.get(s["sid"], 0) + 1

    def node(s: dict) -> dict:
        return {"name": s.get("sortname") or s["alias"], "alias": s["alias"],
                "count": counts.get(s["sid"], 0), "children": []}

    roots = [s for s in sorts.values() if s.get("pid") == "0"]
    roots.sort(key=lambda s: (int(s.get("taxis") or 0), int(s["sid"])))
    categories = []
    for s in roots:
        n = node(s)
        kids = sorted([x for x in sorts.values() if x.get("pid") == s["sid"]],
                      key=lambda x: (int(x.get("taxis") or 0), int(x["sid"])))
        n["children"] = [node(k) for k in kids]
        if n["count"] or n["children"]:
            categories.append(n)

    # ---- 存档：年 → 月 ----
    months: dict[str, int] = {}
    for p in kept:
        if p["type"] == "page":
            continue
        d = iso_date(p.get("date"))
        ym = d[:7].replace("-", "") if d else ""
        if ym:
            months[ym] = months.get(ym, 0) + 1
    by_year: dict[str, list] = {}
    for ym, n in sorted(months.items()):
        by_year.setdefault(ym[:4], []).append({"ym": ym, "label": f"{int(ym[4:])}月", "count": n})
    archives = [{"year": y, "months": ms, "count": sum(m["count"] for m in ms)}
                for y, ms in sorted(by_year.items(), reverse=True)]

    # ---- 最新评论（倒序，链回原文的评论锚点）----
    flat = []
    for gid, items in comments.items():
        url = gid2url.get(gid)
        if not url:
            continue
        for c in items:
            flat.append({
                "url": f"{url}#c{c['id']}",
                "author": c["author"],
                "date": c["date"],
                "text": c["text"],
                "title": "",
            })
    flat.sort(key=lambda c: c["date"], reverse=True)

    titles = {}
    for p in kept:
        titles[gid2url.get(p["gid"], "")] = p["title"]
    for c in flat:
        c["title"] = titles.get(c["url"].split("#")[0], "")
        if len(c["text"]) > 160:
            c["text"] = c["text"][:160] + "…"

    (data / "latest_comments.json").write_text(
        json.dumps(flat[:400], ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    # 侧栏用的短摘要：太长会把侧栏撑得很高
    sidebar_comments = [dict(c, text=(c["text"][:64] + "…") if len(c["text"]) > 64 else c["text"])
                        for c in flat[:6]]

    # ---- 随机文章候选 ----
    urls = [{"t": p["title"], "u": gid2url[p["gid"]]}
            for p in kept if p["type"] != "page" and gid2url.get(p["gid"])]
    (data / "random.json").write_text(
        json.dumps(urls, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    # ---- 站点统计 ----
    views = sum(int(p.get("views") or 0) for p in kept if p["type"] != "page")
    stats = {
        "posts": sum(1 for p in kept if p["type"] != "page"),
        "pages": sum(1 for p in kept if p["type"] == "page"),
        "comments": sum(len(v) for v in comments.values()),
        "views": views,
        "categories": len(categories),
        "forum_topics": forum_topics,
        "forum_posts": forum_posts,
    }
    (data / "nav.json").write_text(json.dumps({
        "categories": categories,
        "archives": archives,
        "stats": stats,
        "latest_comments": sidebar_comments,
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    # ---- 全文搜索索引 ----
    corpus = [c for c in read_corpus(root) if c["url"] not in ("/404.html",)]
    index = [{"u": c["url"], "t": c["title"], "c": c["category"], "g": c["tags"],
              "d": c["date"], "x": c["text"]} for c in corpus]
    target = root / "static" / "search-index.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")),
                      encoding="utf-8")

    # ---- 三个生成页 ----
    gen = root / "content" / "_gen"
    gen.mkdir(parents=True, exist_ok=True)

    rows = ["---", 'title: "全部评论"', 'url: "/comments/"', "---", "",
            f"按时间倒序的最新 {min(400, len(flat))} 条评论（全站共 {stats['comments']} 条）。"
            "完整评论在各篇文章页底部，也可从[数据存档](/archive/)整体下载。", "",
            "| 时间 | 评论者 | 评论 | 出处 |", "| --- | --- | --- | --- |"]
    for c in flat[:400]:
        text = c["text"].replace("|", "／").replace("\n", " ")
        rows.append(f"| {c['date'][:10]} | {c['author']} | {text} | "
                    f"[{c['title'][:28]}]({c['url']}) |")
    (gen / "comments.md").write_text("\n".join(rows) + "\n", encoding="utf-8")

    (gen / "random.md").write_text(
        "---\n"
        'title: "随便看看"\n'
        'url: "/random/"\n'
        "layout: \"random\"\n"
        "---\n\n"
        "正在随机挑一篇文章……\n", encoding="utf-8")

    nav_rows = ["---", 'title: "站内导航"', 'url: "/nav/"', "---", "",
                f"本站共 {stats['posts']} 篇文章、{stats['comments']} 条评论、"
                f"{stats['forum_topics']} 个讨论区存档主题，累计阅读 {stats['views']:,} 次。", ""]
    nav_rows.append("## 分类")
    for c in categories:
        nav_rows.append(f"- [{c['name']}（{c['count']}）](/sort/{c['alias']}/)")
        for k in c["children"]:
            nav_rows.append(f"  - [{k['name']}（{k['count']}）](/sort/{k['alias']}/)")
    nav_rows.append("")
    nav_rows.append("## 文章存档")
    for a in archives:
        months_txt = " · ".join(f"[{m['label']}](/record/{m['ym']}/)" for m in a["months"])
        nav_rows.append(f"- **{a['year']}年**（{a['count']} 篇）：{months_txt}")
    nav_rows.append("")
    nav_rows.append("## 站内入口")
    nav_rows += ["- [留言板](/message_board.html)", "- [全部评论](/comments/)",
                 "- [随便看看](/random/)", "- [全站数据存档](/archive/)",
                 "- [讨论区存档](/forum/)", "- [站内搜索](/search/)"]
    (gen / "nav.md").write_text("\n".join(nav_rows) + "\n", encoding="utf-8")

    n_cats = sum(len(c["children"]) for c in categories)
    report.append(f"  侧栏数据：分类 {len(categories)} 个一级/{n_cats} 个两级、"
                  f"存档 {len(archives)} 年、最新评论 {min(400, len(flat))} 条")
    report.append(f"  搜索索引：{len(index)} 篇，{(target.stat().st_size) / 1e6:.1f} MB")
