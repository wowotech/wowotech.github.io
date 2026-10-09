"""把 emlog / PunBB 的 dump 转成静态站语料与存档。

产出（均在仓库内）：
  content/posts/<分类>/<slug>.md   文章正文 + front matter（含原 URL，保外链）
  content/<alias>.md               独立页面（about / contact_us / message_board …）
  content/forum/<topic>.md         论坛真实主题（2016-2019），只读档案
  data/comments/<gid>.json         每篇文章的冻结评论
  data/site.json / data/forum.json / data/urlmap.json
  static/archive/*.sqlite|json     可下载存档（公开版已去除邮箱与 IP）

用法：
  python tools/convert.py --emlog recon/emlog_20250207.sql --full recon/db_20240923.sql
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import bbcode  # noqa: E402
import normalize_links  # noqa: E402
import site_data  # noqa: E402
import clean_html  # noqa: E402
import sqldump  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CST = timezone(timedelta(hours=8))
BASE_RE = re.compile(r"^https?://(?:www\.)?wowotech\.net(?::\d+)?", re.I)

# 论坛垃圾潮：2022 年的 7.8 万条阿拉伯语二元期权帖，一刀切掉 2022 及以后
FORUM_SPAM_CUTOFF = int(datetime(2022, 1, 1, tzinfo=CST).timestamp())

# 这些根路径由站点自身占用，不能作为文章别名（否则会撞掉 404 页、sitemap 等）
RESERVED_PATHS = {"/404.html", "/index.html", "/sitemap.xml", "/robots.txt",
                  "/llms.txt", "/index.xml", "/favicon.ico"}

COMMENT_SPAM_HINTS = (
    "viagra", "levitra", "cialis", "binary option", "payday loan", "casino",
    "replica watch", "fake passport", "الخيارات الثنائية", "tadalafil",
)


def iso(ts) -> str:
    try:
        return datetime.fromtimestamp(int(ts), CST).isoformat()
    except (TypeError, ValueError):
        return ""


def has_arabic(s: str) -> bool:
    return any("؀" <= c <= "ۿ" for c in s or "")


def comment_is_spam(text: str) -> bool:
    t = (text or "").lower()
    if has_arabic(t):
        return True
    return any(h in t for h in COMMENT_SPAM_HINTS)


def parse_gid_list(s: str) -> list[str]:
    """emlog 的 emlog_tag.gid 存的是逗号包裹的文章 id 列表，例如 ",7,19,"。"""
    return [x for x in (s or "").replace(" ", "").split(",") if x]


def yaml_str(s: str) -> str:
    return json.dumps(s or "", ensure_ascii=False)


def load_emlog(path: Path) -> dict:
    return {
        "posts": sqldump.records(path, "emlog_blog"),
        "sorts": sqldump.records(path, "emlog_sort"),
        "users": sqldump.records(path, "emlog_user"),
        "tags": sqldump.records(path, "emlog_tag"),
        "comments": sqldump.records(path, "emlog_comment"),
        "attachments": sqldump.records(path, "emlog_attachment"),
        "options": sqldump.records(path, "emlog_options"),
        "navi": sqldump.records(path, "emlog_navi"),
        "links": sqldump.records(path, "emlog_link"),
    }


def load_live(path: Path) -> dict:
    """读取 tools/sync.py 从活库导出的 JSON；数值统一转成字符串，与 dump 解析结果保持一致。"""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    out = {}
    for table, rows in (raw.get("tables") or {}).items():
        out[table] = [{k: (None if v is None else str(v)) for k, v in row.items()} for row in rows]
    out["__php__"] = [{"version": raw.get("php", "?")}]
    return out


def pick(live: dict, suffix: str):
    """按表名后缀取数据，兼容 emlog_ 前缀与无前缀的 PunBB 表。"""
    for table, rows in live.items():
        if table == suffix or table.endswith("_" + suffix):
            return rows
    return None


def load_forum(path: Path) -> dict:
    return {
        "topics": sqldump.records(path, "topics"),
        "posts": sqldump.records(path, "posts"),
        "users": sqldump.records(path, "users"),
        "forums": sqldump.records(path, "forums"),
        "categories": sqldump.records(path, "categories"),
    }


class Rewriter:
    """把正文里的原始资源地址改写成本站路径，并登记需要下载的附件。"""

    def __init__(self, gid2url: dict[str, str]):
        self.gid2url = gid2url
        self.assets: set[str] = set()

    def url(self, u: str) -> str:
        u = (u or "").strip()
        if u.lower().startswith("file:"):
            return ""
        m = re.match(r"^(https?://(?:www\.)?wowotech\.net)(/.*)?$", u, re.I)
        if m:
            path = m.group(2) or "/"
            q = re.match(r"^/\?post=(\d+)", path)
            if q:
                return self.gid2url.get(q.group(1), "/")
            head, _, tail = path.rpartition("/")
            # 缩略图 thum-xxx.jpg 换回原图，画质更好；路径保持 /content/uploadfile/... 原样，
            # 这样历史上被外部引用的图片地址继续有效
            tail = re.sub(r"^thum-", "", tail)
            new = f"{head}/{tail}"
            if "/content/uploadfile/" in new:
                self.assets.add(new)
            return new
        return u

    def html(self, raw: str) -> str:
        def fix(m: re.Match) -> str:
            attr, quote, value = m.group(1), m.group(2), m.group(3)
            return f'{attr}={quote}{self.url(value)}{quote}'

        raw = re.sub(r'(href|src)=(["\'])(.*?)\2', fix, raw)
        # Word 留下的本地文件链接：去掉链接本身，保留文字
        raw = re.sub(r'<a[^>]*href=""[^>]*>(.*?)</a>', r"\1", raw, flags=re.S)
        return raw


# ---------------------------------------------------------------- emlog 文章

def build_url(post: dict, sorts: dict[str, dict]) -> str:
    alias = (post.get("alias") or "").strip()
    if post.get("type") == "page":
        return f"/{alias}.html" if alias else f"/{post['gid']}.html"
    sa = (sorts.get(post.get("sortid"), {}) or {}).get("alias", "")
    if alias:
        return f"/{sa}/{alias}.html" if sa else f"/{alias}.html"
    return f"/{sa}/{post['gid']}.html" if sa else f"/{post['gid']}.html"


def convert_posts(data: dict, out: Path, rw: Rewriter, report: list[str]):
    sorts = {r["sid"]: r for r in data["sorts"]}
    users = {r["uid"]: r for r in data["users"]}
    tags: dict[str, list[str]] = {}
    for row in data["tags"]:
        name = (row.get("tagname") or "").strip()
        if not name:
            continue
        for g in parse_gid_list(row.get("gid")):
            tags.setdefault(g, []).append(name)

    kept = [p for p in data["posts"] if p["hide"] != "y" and p["checked"] != "n"]
    report.append(f"文章：总 {len(data['posts'])}，发布 {len(kept)}"
                  f"（隐藏 {sum(1 for p in data['posts'] if p['hide']=='y')}，"
                  f"未审核 {sum(1 for p in data['posts'] if p['checked']=='n')}）")

    gid2url = {p["gid"]: build_url(p, sorts) for p in kept}
    rw.gid2url = gid2url

    n_posts = n_pages = 0
    seen_paths: set[str] = set()
    for p in kept:
        url = gid2url[p["gid"]]
        body = clean_html.clean(rw.html(p["content"] or ""))
        sort = sorts.get(p["sortid"]) or {}
        author = users.get(p["author"]) or {}
        name = author.get("nickname") or author.get("username") or ""
        date = iso(p["date"])

        fm = ["---",
              f"title: {yaml_str(p['title'])}",
              f"date: {date}",
              f"url: {yaml_str(url)}",
              f"gid: {yaml_str(p['gid'])}",
              # 用 emlog_type 存原值：若写成 type，会覆盖 Hugo 由目录推断的段落类型，
              # 首页 /posts/ 的筛选就会全部落空
              f"emlog_type: {yaml_str(p['type'])}"]
        # 首页摘要：优先用作者写的 excerpt，没有就用正文开头（与原站行为一致）
        summary = ""
        if p.get("excerpt"):
            summary = re.sub(r"\s+", " ", html.unescape(
                re.sub(r"<[^>]+>", " ", p["excerpt"]))).strip()
        if not summary:
            summary = site_data.plain_text(body)
        fm.append(f"summary: {yaml_str(summary[:200])}")
        if name:
            fm.append(f"author: {yaml_str(name)}")
        if sort:
            fm.append(f"category: {yaml_str(sort.get('sortname', ''))}")
            fm.append(f"category_alias: {yaml_str(sort.get('alias', ''))}")
        if tags.get(p["gid"]):
            fm.append("tags: [" + ", ".join(yaml_str(t) for t in tags[p["gid"]] if t) + "]")
        fm.append(f"views: {int(p.get('views') or 0)}")
        fm.append(f"comment_count: {int(p.get('comnum') or 0)}")
        # 两种历史写法都能打开，保留 gid 形式做重定向
        alt = []
        if p["type"] != "page":
            sa = (sort.get("alias") or "")
            if (p.get("alias") or "").strip() and sa:
                alt.append(f"/{sa}/{p['gid']}.html")     # 分类+gid 形式
            alt.append(f"/{p['gid']}.html")              # 根路径 gid 形式
        alt = [a for a in alt if a != url and a not in RESERVED_PATHS]
        if alt:
            fm.append("aliases:")
            fm.extend(f"  - {yaml_str(a)}" for a in alt)
        fm.append("---")

        if p["type"] == "page":
            dest = out / "content" / f"{p['alias'] or p['gid']}.md"
            n_pages += 1
        else:
            sa = sort.get("alias") or "_uncategorized"
            dest = out / "content" / "posts" / sa / f"{p['alias'] or p['gid']}.md"
            n_posts += 1
        # Windows / macOS 的文件名不区分大小写，而 emlog 里存在只差大小写的别名
        # （如 PELT 与 pelt，原站是 Linux，两者是不同文章）。加 gid 后缀避免源文件互相覆盖；
        # 文章对外 URL 不受影响，仍按 front matter 里的 url 生成。
        key = str(dest).lower()
        if key in seen_paths:
            dest = dest.with_name(f"{dest.stem}_{p['gid']}{dest.suffix}")
            key = str(dest).lower()
            report.append(f"  注意：{p['gid']} 的别名与已有文件仅大小写不同，存为 {dest.name}")
        seen_paths.add(key)

        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("\n".join(fm) + "\n\n" + body, encoding="utf-8")

    report.append(f"  写入 content/：文章 {n_posts} 篇，页面 {n_pages} 个")
    return kept, sorts, users, gid2url


def convert_comments(data: dict, kept: list[dict], out: Path, report: list[str]) -> tuple[dict, int]:
    # 页面（留言板、关于我们）同样有评论，必须一起保留
    kept_gids = {p["gid"] for p in kept}
    by_gid: dict[str, list[dict]] = {}
    dropped_hidden = dropped_spam = 0
    for c in data["comments"]:
        if c["gid"] not in kept_gids:
            continue
        if c["hide"] == "y":
            dropped_hidden += 1
            continue
        text = c.get("comment") or ""
        if comment_is_spam(text):
            dropped_spam += 1
            continue
        by_gid.setdefault(c["gid"], []).append({
            "id": c["cid"],
            "parent": c["pid"],
            "date": iso(c["date"]),
            "author": (c.get("poster") or "").strip(),
            "site": (c.get("url") or "").strip(),
            "text": text,
        })

    dest = out / "data" / "comments"
    dest.mkdir(parents=True, exist_ok=True)
    for gid, items in by_gid.items():
        items.sort(key=lambda x: x["date"])
        (dest / f"{gid}.json").write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")

    total = sum(len(v) for v in by_gid.values())
    report.append(f"评论：导出 {total} 条到 {len(by_gid)} 篇"
                  f"（隐藏 {dropped_hidden}，判为垃圾 {dropped_spam}）")
    return by_gid, total


# ---------------------------------------------------------------- 论坛档案

def convert_forum(raw: dict, out: Path, report: list[str]) -> dict:
    topics = raw["topics"]
    posts = raw["posts"]
    users = raw["users"]
    forums = raw["forums"]
    cats = raw["categories"]

    real = [t for t in topics if int(t["posted"] or 0) < FORUM_SPAM_CUTOFF]
    real_ids = {t["id"] for t in real}
    real_posts = [p for p in posts if p["topic_id"] in real_ids]
    report.append(f"论坛：主题 {len(topics)} → 保留 {len(real)}"
                  f"（丢弃 2022 年垃圾 {len(topics) - len(real)}）；"
                  f"帖子 {len(posts)} → 保留 {len(real_posts)}")

    by_topic: dict[str, list[dict]] = {}
    for p in real_posts:
        by_topic.setdefault(p["topic_id"], []).append(p)

    forum_by_id = {f["id"]: f for f in forums}
    cat_by_id = {c["id"]: c for c in cats}

    (out / "data").mkdir(parents=True, exist_ok=True)
    (out / "content" / "forum").mkdir(parents=True, exist_ok=True)

    n = 0
    for t in real:
        replies = sorted(by_topic.get(t["id"], []), key=lambda p: int(p["posted"] or 0))
        blocks = []
        for p in replies:
            body = bbcode.to_markdown(p.get("message") or "")
            blocks.append(f'<div class="post">\n<p class="meta">'
                          f'<strong>{html.escape(p.get("poster") or "")}</strong> · '
                          f'{iso(p["posted"])[:16].replace("T", " ")}</p>\n'
                          f'{_md_to_html(body)}\n</div>')
        forum = forum_by_id.get(t["forum_id"]) or {}
        topic_url = f"/forum/{t['id']}.html"
        fm = ["---",
              f"title: {yaml_str(t.get('subject') or '(无标题)')}",
              f"date: {iso(t['posted'])}",
              f"lastmod: {iso(t.get('last_post') or t['posted'])}",
              f"url: {yaml_str(topic_url)}",
              f"poster: {yaml_str(t.get('poster') or '')}",
              f"forum: {yaml_str(forum.get('forum_name') or '')}",
              f"replies: {len(replies) - 1}",
              f"views: {int(t.get('num_views') or 0)}",
              "---",
              f"> 本文是原「蜗窝讨论区」的历史存档（{iso(t['posted'])[:10]}），"
              f"来自版块「{forum.get('forum_name') or '未知'}」，共 {len(replies)} 帖。"
              f"讨论区已停止服务，此处仅供查阅。", ""]
        (out / "content" / "forum" / f"{t['id']}.md").write_text(
            "\n".join(fm) + "\n\n" + "\n\n".join(blocks) + "\n", encoding="utf-8")
        n += 1

    # 版块索引
    counts: dict[str, int] = {}
    for t in real:
        counts[t["forum_id"]] = counts.get(t["forum_id"], 0) + 1
    # 这是 forum 段落的 _index，Hugo 会自然渲染到 /forum/，无需指定 url
    idx = ["---", "title: \"蜗窝讨论区（存档）\"", "---", "",
           "原「蜗窝讨论区」于 2016–2019 年运行，2022 年遭垃圾帖灌爆后停摆。",
           "这里保留了全部真实主题的只读存档，注册用户与历史帖完整可查。", "",
           "- [成员名录](/forum/members.html)", ""]
    for f in forums:
        if counts.get(f["id"]):
            cat = cat_by_id.get(f["cat_id"]) or {}
            idx.append(f"## {cat.get('cat_name', '')} / {f['forum_name']}")
            idx.append(f.get("forum_desc") or "")
            idx.append("")
            for t in sorted([x for x in real if x["forum_id"] == f["id"]],
                            key=lambda x: int(x["posted"] or 0), reverse=True):
                idx.append(f"- [{t.get('subject') or '(无标题)'}](/forum/{t['id']}.html) "
                           f"· {iso(t['posted'])[:10]} · {t.get('poster') or ''} "
                           f"· {int(t.get('num_replies') or 0) + 1} 帖")
            idx.append("")
    (out / "content" / "forum" / "_index.md").write_text("\n".join(idx), encoding="utf-8")

    # 成员名录：只列真正发过言的
    active = sorted([u for u in users if int(u.get("num_posts") or 0) > 0],
                    key=lambda u: -int(u.get("num_posts") or 0))
    mem = ["---", "title: \"讨论区成员名录\"", "url: \"/forum/members.html\"", "---", "",
           f"共有 {len(users)} 个注册账号，其中 {len(active)} 位发过言。"
           "（邮箱等联系方式不在公开存档中。）", "",
           "| 用户名 | 帖数 | 注册时间 | 最后到访 |", "| --- | --- | --- | --- |"]
    for u in active:
        mem.append(f"| {u.get('username')} | {int(u.get('num_posts') or 0)} | "
                   f"{iso(u.get('registered'))[:10]} | {iso(u.get('last_visit'))[:10]} |")
    (out / "content" / "forum" / "members.md").write_text("\n".join(mem), encoding="utf-8")

    (out / "data" / "forum.json").write_text(json.dumps({
        "topics": len(real), "posts": len(real_posts), "users": len(users),
        "active_users": len(active),
        "forums": [{"name": f["forum_name"], "desc": f.get("forum_desc") or "",
                    "topics": counts.get(f["id"], 0)} for f in forums],
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    report.append(f"  写入 content/forum/：主题页 {n} 个 + 索引 + 成员名录")
    return {"topics": real, "posts": real_posts, "users": users, "active": active,
            "forums": forums}


def _md_to_html(md: str) -> str:
    """论坛正文里既有 BBCode 转出的 Markdown，也有行内 HTML，交给 Hugo 前先粗转一下段落。"""
    if not md.strip():
        return ""
    try:
        import markdown  # 可选依赖
        return markdown.markdown(md, extensions=["fenced_code", "tables"])
    except ImportError:
        parts = [p.strip() for p in re.split(r"\n\s*\n", md) if p.strip()]
        out = []
        for p in parts:
            if p.startswith("- "):
                items = "".join(f"<li>{html.escape(x[2:].strip())}</li>"
                                for x in p.splitlines() if x.startswith("- "))
                out.append(f"<ul>{items}</ul>")
            elif p.startswith("```"):
                out.append(f"<pre>{html.escape(p.strip('`').strip())}</pre>")
            else:
                out.append(f"<p>{html.escape(p).replace(chr(10), '<br/>')}</p>")
        return "\n".join(out)



# ---------------------------------------------------------------- 索引页

def write_index_pages(emlog: dict, kept: list[dict], sorts: dict, gid2url: dict,
                      out: Path, report: list[str]) -> None:
    """生成分类页 /sort/<别名>、月度存档 /record/<YYYYMM>、标签页 /tag/<标签名>。

    这三种地址都在原站 sitemap 里（标签页多达 526 个），生成它们才能保住外链，
    而不是只保住文章本身的地址。
    """
    gen = out / "content" / "_gen"
    gen.mkdir(parents=True, exist_ok=True)
    title_of = {p["gid"]: p["title"] for p in kept}
    date_of = {p["gid"]: iso(p["date"]) for p in kept}

    def page(name: str, title: str, url: str, intro: str, gids: list[str]) -> None:
        rows = sorted([g for g in gids if g in title_of], key=lambda g: date_of[g], reverse=True)
        body = [f"---", f"title: {yaml_str(title)}", f"url: {yaml_str(url)}", "---", "", intro, ""]
        for g in rows:
            body.append(f"- [{title_of[g]}]({gid2url[g]}) <span class=\"small\">{date_of[g][:10]}</span>")
        (gen / name).write_text("\n".join(body) + "\n", encoding="utf-8")
        return len(rows)

    n_cat = 0
    for sid, s in sorts.items():
        gids = [p["gid"] for p in kept if p["sortid"] == sid and p["type"] != "page"]
        n_cat += 1
        intro = (f"分类「{s.get('sortname')}」共 {len(gids)} 篇。" if gids
                 else f"分类「{s.get('sortname')}」下暂无已发布的文章。")
        page(f"sort-{s['alias']}.md", s.get("sortname") or s["alias"],
             f"/sort/{s['alias']}", intro, gids)

    months: dict[str, list[str]] = {}
    for p in kept:
        if p["type"] == "page":
            continue
        months.setdefault(iso(p["date"])[:7].replace("-", ""), []).append(p["gid"])
    for ym, gids in months.items():
        page(f"record-{ym}.md", f"{ym[:4]}年{int(ym[4:])}月",
             f"/record/{ym}", f"{ym[:4]}年{int(ym[4:])}月共 {len(gids)} 篇。", gids)

    # 作者页：原站地址是 /author/<uid>，内容里多处引用
    author_name = {u["uid"]: (u.get("nickname") or u.get("username") or "")
                   for u in emlog["users"]}
    by_author: dict[str, list[str]] = {}
    for p in kept:
        if p["type"] != "page":
            by_author.setdefault(p["author"], []).append(p["gid"])
    for uid, gids in by_author.items():
        name = author_name.get(uid) or f"作者 {uid}"
        page(f"author-{uid}.md", f"作者：{name}", f"/author/{uid}/",
             f"{name} 共发表 {len(gids)} 篇。", gids)

    tag_gids: dict[str, list[str]] = {}
    for row in emlog["tags"]:
        name = (row.get("tagname") or "").strip()
        if not name:
            continue
        for g in parse_gid_list(row.get("gid")):
            if g in title_of:
                tag_gids.setdefault(name, []).append(g)
    for name, gids in tag_gids.items():
        page(f"tag-{hashlib.md5(name.encode()).hexdigest()[:12]}.md", f"标签：{name}",
             f"/tag/{name}", f"带标签「{name}」的文章共 {len(gids)} 篇。", gids)

    report.append(f"  索引页：分类 {n_cat} 个，月度存档 {len(months)} 个，"
                  f"标签页 {len(tag_gids)} 个，作者页 {len(by_author)} 个")



def write_ai_surface(out: Path, emlog: dict, kept: list[dict], sorts: dict,
                     gid2url: dict, forum: dict, report: list[str], site_url: str) -> None:
    """生成 robots.txt 与 llms.txt：让 AI 爬虫和助手能发现并取用这份知识。"""
    static = out / "static"
    static.mkdir(parents=True, exist_ok=True)
    posts = [p for p in kept if p["type"] != "page"]

    robots = """User-agent: *
Allow: /
Disallow: /admin/
Disallow: /forum/members.html

# 欢迎 AI 助手与搜索引擎索引本站内容（CC BY-SA 4.0，允许镜像与用于模型训练）
User-agent: GPTBot
Allow: /
User-agent: ClaudeBot
Allow: /
User-agent: Claude-Web
Allow: /
User-agent: Google-Extended
Allow: /
User-agent: PerplexityBot
Allow: /
User-agent: Applebot-Extended
Allow: /
User-agent: Bytespider
Allow: /
User-agent: CCBot
Allow: /

Sitemap: %s/sitemap.xml
""" % site_url
    (static / "robots.txt").write_text(robots, encoding="utf-8")

    cat_counts = {}
    for p in posts:
        s = sorts.get(p["sortid"]) or {}
        if s.get("sortname"):
            cat_counts[s["sortname"]] = cat_counts.get(s["sortname"], 0) + 1

    lines = [
        "# 蜗窝科技（wowotech.net）",
        "",
        "> 嵌入式 Linux 内核、ARM 架构与驱动开发的中文技术笔记存档，"
        f"2014–2025 年共 {len(posts)} 篇技术文章，另有 {len(forum['topics'])} 个原讨论区主题的只读存档。"
        "内容以内核子系统源码分析、协议与硬件调试记录为主，附有读者评论。",
        "",
        "内容以 CC BY-SA 4.0 开放，欢迎索引、镜像与用于模型训练。",
        "",
        "## 直接取用的数据",
        f"- [全站结构化数据（SQLite）]({site_url}/archive/wowotech-archive.sqlite)："
        "文章正文 HTML 原文、全部评论、讨论区主题与帖子、分类与标签",
        f"- [文章列表（RSS）]({site_url}/index.xml)",
        f"- [站点地图]({site_url}/sitemap.xml)",
        f"- [讨论区存档]({site_url}/forum/)：2016–2019 年的真实技术讨论",
        "",
        "## 分类",
    ]
    for name, n in sorted(cat_counts.items(), key=lambda x: -x[1]):
        lines.append(f"- {name}：{n} 篇")
    lines += [
        "",
        "## 说明",
        "- 全部文章均为原创技术笔记，作者为蜗窝（wowo）及合作者。",
        "- 原站讨论区在 2022 年遭垃圾帖灌爆后停摆，本站仅保留其中的真实讨论。",
        "- 评论区已冻结为只读存档，不提供发布入口。",
        "",
    ]
    (static / "llms.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    report.append("  AI 入口：static/robots.txt（放行主流 AI 爬虫）、static/llms.txt")


# ---------------------------------------------------------------- 存档

def write_archive(out: Path, emlog: dict, kept: list[dict], comments: dict,
                  forum: dict, forum_raw: dict, private_dir: Path, report: list[str]):
    def build(path: Path, with_pii: bool):
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            path.unlink()
        db = sqlite3.connect(path)
        db.executescript("""
        CREATE TABLE posts(gid TEXT PRIMARY KEY, title TEXT, url TEXT, date TEXT,
                           category TEXT, author TEXT, views INT, comments INT, body TEXT);
        CREATE TABLE comments(id TEXT PRIMARY KEY, gid TEXT, parent TEXT, date TEXT,
                              author TEXT, site TEXT, text TEXT);
        CREATE TABLE forum_topics(id TEXT PRIMARY KEY, subject TEXT, poster TEXT,
                                  posted TEXT, forum TEXT, replies INT, views INT);
        CREATE TABLE forum_posts(id TEXT PRIMARY KEY, topic_id TEXT, poster TEXT,
                                 posted TEXT, message TEXT);
        CREATE TABLE blog_users(uid TEXT PRIMARY KEY, username TEXT, nickname TEXT,
                                role TEXT, email TEXT, registered_hint TEXT);
        CREATE TABLE forum_users(id TEXT PRIMARY KEY, username TEXT, email TEXT,
                                 num_posts INT, registered TEXT, last_visit TEXT);
        CREATE TABLE categories(sid TEXT PRIMARY KEY, name TEXT, alias TEXT, parent TEXT);
        CREATE TABLE tags(gid TEXT, tagname TEXT);
        CREATE TABLE attachments(aid TEXT PRIMARY KEY, gid TEXT, filename TEXT,
                                 path TEXT, size INT);
        """)
        body_of = {p["gid"]: p for p in emlog["posts"]}
        for p in kept:
            db.execute("INSERT INTO posts VALUES(?,?,?,?,?,?,?,?,?)", (
                p["gid"], p["title"], build_url(p, {r["sid"]: r for r in emlog["sorts"]}),
                iso(p["date"]), "", "", int(p.get("views") or 0),
                int(p.get("comnum") or 0), p.get("content") or ""))
        for gid, items in comments.items():
            for c in items:
                db.execute("INSERT INTO comments VALUES(?,?,?,?,?,?,?)",
                           (c["id"], gid, c["parent"], c["date"], c["author"], c["site"], c["text"]))
        forum_by_id = {f["id"]: f for f in forum_raw["forums"]}
        for t in forum["topics"]:
            db.execute("INSERT INTO forum_topics VALUES(?,?,?,?,?,?,?)", (
                t["id"], t.get("subject"), t.get("poster"), iso(t["posted"]),
                (forum_by_id.get(t["forum_id"]) or {}).get("forum_name", ""),
                int(t.get("num_replies") or 0), int(t.get("num_views") or 0)))
        for p in forum["posts"]:
            db.execute("INSERT INTO forum_posts VALUES(?,?,?,?,?)", (
                p["id"], p["topic_id"], p.get("poster"), iso(p["posted"]), p.get("message")))
        for u in emlog["users"]:
            db.execute("INSERT INTO blog_users VALUES(?,?,?,?,?,?)", (
                u["uid"], u["username"], u.get("nickname"), u.get("role"),
                u.get("email") if with_pii else None, ""))
        for u in forum["users"]:
            db.execute("INSERT INTO forum_users VALUES(?,?,?,?,?,?)", (
                u["id"], u.get("username"), u.get("email") if with_pii else None,
                int(u.get("num_posts") or 0), iso(u.get("registered")), iso(u.get("last_visit"))))
        for s in emlog["sorts"]:
            db.execute("INSERT INTO categories VALUES(?,?,?,?)",
                       (s["sid"], s.get("sortname"), s.get("alias"), s.get("pid")))
        for t in emlog["tags"]:
            db.execute("INSERT INTO tags VALUES(?,?)", (t["gid"], t.get("tagname")))
        for a in emlog["attachments"]:
            db.execute("INSERT INTO attachments VALUES(?,?,?,?,?)", (
                a["aid"], a["blogid"], a.get("filename"), a.get("filepath"),
                int(a.get("filesize") or 0)))
        db.commit()
        db.close()

    pub = out / "static" / "archive"
    build(pub / "wowotech-archive.sqlite", with_pii=False)
    build(private_dir / "wowotech-archive-full.sqlite", with_pii=True)
    report.append(f"存档：公开版 {pub/'wowotech-archive.sqlite'}（无邮箱/IP），"
                  f"全量版留本地 {private_dir}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--emlog", default="recon/emlog_20250207.sql")
    ap.add_argument("--full", default="recon/db_20240923.sql")
    ap.add_argument("--out", default=".")
    ap.add_argument("--private", default="../wowotech-archive-private")
    ap.add_argument("--live", help="tools/sync.py 从活库导出的 JSON，优先于 dump")
    args = ap.parse_args()

    out = Path(args.out).resolve()
    report: list[str] = []

    emlog = load_emlog(Path(args.emlog))
    forum_raw = load_forum(Path(args.full))
    if args.live:
        live = load_live(Path(args.live))
        for suffix, key in (("blog", "posts"), ("comment", "comments"), ("user", "users"),
                            ("sort", "sorts"), ("tag", "tags"), ("attachment", "attachments"),
                            ("options", "options"), ("navi", "navi"),
                            ("link", "links")):
            rows = pick(live, suffix)
            if rows is not None:
                emlog[key] = rows
        for name in ("topics", "posts", "users", "forums", "categories"):
            rows = pick(live, name)
            if rows is not None:
                forum_raw[name] = rows
        report.append(f"数据源：活库导出（PHP {live.get('__php__', [{}])[0].get('version')}）"
                      f"＋ dump 补齐，导出时间 {datetime.fromtimestamp(json.loads(Path(args.live).read_text(encoding='utf-8'))['generated_at'], CST):%Y-%m-%d %H:%M}")
    else:
        report.append("数据源：仅本地 dump（未联网取活库）")

    rw = Rewriter({})
    kept, sorts, users, gid2url = convert_posts(emlog, out, rw, report)
    comments, n_comments = convert_comments(emlog, kept, out, report)
    write_index_pages(emlog, kept, sorts, gid2url, out, report)
    forum = convert_forum(forum_raw, out, report)

    (out / "data").mkdir(parents=True, exist_ok=True)
    (out / "data" / "urlmap.json").write_text(
        json.dumps(gid2url, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    # slug → 文章地址：404 页面用它兜住「分类写错/缺后缀」的外来链接
    slugmap: dict[str, str] = {}
    for url in gid2url.values():
        slug = re.sub(r"\.html$", "", url.rstrip("/").rsplit("/", 1)[-1]).lower()
        if slug and slug not in slugmap:
            slugmap[slug] = url
    (out / "data" / "slugmap.json").write_text(
        json.dumps(slugmap, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    opts = {}
    for o in emlog["options"]:
        key = o.get("option_name") or o.get("name")
        if key:
            val = o.get("option_value")
            opts[key] = o.get("value") if val is None else val
    (out / "data" / "site.json").write_text(json.dumps({
        "title": opts.get("blogname", "蜗窝科技"),
        "description": opts.get("bloginfo", ""),
        "url": (opts.get("blogurl") or "http://www.wowotech.net").rstrip("/"),
        # 导航改用白名单重建：emlog 的 navi 表里有「登录」「微语」这类动态入口，
        # 在静态站上是死链（微语表本身是空的），所以只保留确实有页面的几项
        "nav": [
            {"name": "博客", "url": "/"},
            {"name": "关于蜗窝", "url": "/about.html"},
            {"name": "项目", "url": "/sort/project"},
            {"name": "讨论区存档", "url": "/forum/"},
            {"name": "联系我们", "url": "/contact_us.html"},
            {"name": "支持与合作", "url": "/support_us.html"},
            {"name": "留言板", "url": "/message_board.html"},
            {"name": "数据存档", "url": "/archive/"},
        ],
        "categories": [{"name": s.get("sortname"), "alias": s.get("alias"),
                        "posts": sum(1 for p in kept if p["sortid"] == s["sid"])}
                       for s in sorted(emlog["sorts"], key=lambda x: int(x.get("taxis") or 0))],
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    site_url = (opts.get("blogurl") or "https://www.wowotech.net").rstrip("/")
    write_ai_surface(out, emlog, kept, sorts, gid2url, forum, report, site_url)
    write_archive(out, emlog, kept, comments, forum, forum_raw, Path(args.private).resolve(), report)
    site_data.write_nav_data(out, kept, comments, sorts, gid2url,
                             len(forum["topics"]), len(forum["posts"]), report)

    manifest = out / "recon" / "assets.txt"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text("\n".join(sorted(rw.assets)) + "\n", encoding="utf-8")
    report.append(f"附件：正文引用 {len(rw.assets)} 个，清单写入 recon/assets.txt")

    # 直接跑 convert 会把语料恢复成原始状态（链接里的旧地址会回来），
    # 所以这里顺手规范化一遍，保证「生成完就是干净的」
    normalize_links.run(check=False)

    (out / "recon" / "convert_report.txt").write_text("\n".join(report), encoding="utf-8")
    print("\n".join(report))


if __name__ == "__main__":
    main()
