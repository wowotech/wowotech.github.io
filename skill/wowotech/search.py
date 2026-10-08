"""蜗窝科技语料检索（无第三方依赖）。

用法:
  python search.py 中断 线程化            # 关键词检索（多个词按 AND 处理）
  python search.py spinlock --tag 内核同步 --limit 5
  python search.py --show 522             # 打印某篇文章全文与评论
  python search.py kobject --comments     # 连同评论一起检索
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POSTS = ROOT / "content" / "posts"
COMMENTS = ROOT / "data" / "comments"


def read_front_matter(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return {}, text
    _, fm, body = text.split("---", 2)
    meta = {}
    for line in fm.strip().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip('"')
    return meta, body


def load_posts() -> list[dict]:
    out = []
    for path in POSTS.rglob("*.md"):
        meta, body = read_front_matter(path)
        out.append({
            "path": path,
            "title": meta.get("title", path.stem),
            "url": meta.get("url", ""),
            "gid": meta.get("gid", ""),
            "date": meta.get("date", "")[:10],
            "category": meta.get("category", ""),
            "tags": re.findall(r'"([^"]+)"', meta.get("tags", "")),
            "body": body,
            "text": body.lower(),
        })
    return out


def load_comments(gid: str) -> list[dict]:
    f = COMMENTS / f"{gid}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else []


def snippet(text: str, terms: list[str], width: int = 90) -> str:
    flat = re.sub(r"\s+", " ", text)
    low = flat.lower()
    pos = min((low.find(t) for t in terms if low.find(t) >= 0), default=-1)
    if pos < 0:
        return flat[:width]
    start = max(0, pos - width // 3)
    return ("…" if start else "") + flat[start:start + width].strip() + "…"


def search(posts: list[dict], terms: list[str], args) -> list[tuple[int, dict]]:
    hits = []
    for p in posts:
        if args.tag and args.tag not in p["tags"] and args.tag not in p["category"]:
            continue
        if args.category and args.category not in p["category"]:
            continue
        pool = p["text"]
        if args.comments:
            pool += " " + " ".join(c["text"] for c in load_comments(p["gid"])).lower()
        score = 0
        for t in terms:
            n = pool.count(t)
            if not n:
                score = -1
                break
            score += n
            if t in p["title"].lower():
                score += 20          # 标题命中权重更高
            if t in " ".join(p["tags"]).lower():
                score += 5
        if score > 0:
            hits.append((score, p))
    hits.sort(key=lambda x: (-x[0], x[1]["date"]))
    return hits


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("terms", nargs="*", help="检索关键词")
    ap.add_argument("--tag", help="按标签或分类过滤")
    ap.add_argument("--category", help="按分类过滤")
    ap.add_argument("--limit", type=int, default=8)
    ap.add_argument("--comments", action="store_true", help="把评论也纳入检索范围")
    ap.add_argument("--show", help="打印指定文章 id 的全文")
    ap.add_argument("--comments-of", dest="comments_of", help="打印指定文章的评论")
    args = ap.parse_args()

    posts = load_posts()

    if args.show:
        hit = next((p for p in posts if p["gid"] == args.show), None)
        if not hit:
            print(f"没有 gid={args.show} 的文章")
            return 1
        print(f"# {hit['title']}\n{hit['date']} · {hit['category']} · {hit['url']}\n")
        print(hit["body"])
        return 0

    if args.comments_of:
        for c in load_comments(args.comments_of):
            print(f"[{c['date'][:10]}] {c['author']}: {c['text']}\n")
        return 0

    if not args.terms:
        ap.print_help()
        return 1

    terms = [t.lower() for t in args.terms]
    hits = search(posts, terms, args)
    if not hits:
        print(f"没有匹配「{' '.join(args.terms)}」的文章（共 {len(posts)} 篇）")
        return 1

    print(f"命中 {len(hits)} 篇，显示前 {min(args.limit, len(hits))} 篇：\n")
    for score, p in hits[:args.limit]:
        tags = "、".join(p["tags"][:4])
        print(f"● {p['title']}")
        print(f"  {p['date']} · {p['category']}{' · ' + tags if tags else ''} · {p['url']}")
        print(f"  {snippet(p['body'], terms)}")
        if args.comments:
            cs = [c for c in load_comments(p["gid"])
                  if any(t in c["text"].lower() for t in terms)]
            for c in cs[:2]:
                print(f"  └ 评论 [{c['author']}] {snippet(c['text'], terms, 70)}")
        print()
    print("用 --show <gid> 看全文，--comments-of <gid> 看全部评论。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
