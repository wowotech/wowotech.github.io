"""验收：原站 sitemap 里的每一个地址，在新站产物里都要能命中。

这是判断「外链有没有保住」的硬指标——不看主观印象，只看 1008 个旧地址
逐一是否有对应文件（含 Hugo 生成的 alias 重定向页）。
"""
from __future__ import annotations

import re
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "public"
# 原站 sitemap 作为验收基准：优先用刚抓下来的，仓库里也留一份固定副本供 CI 回归
SITEMAP = ROOT / "recon" / "sitemap.xml"
SITEMAP_FIXTURE = ROOT / "tools" / "fixtures" / "origin-sitemap.xml"

# 原站自己就返回 404 的地址（未审核文章），不算回归
KNOWN_DEAD = {"/soft/501.html"}


def candidates(path: str) -> list[str]:
    """一个旧地址可能对应的产物文件路径，按可能性排序。"""
    p = urllib.parse.unquote(path).lstrip("/")
    out = []
    if not p:
        return ["index.html"]
    if p.endswith("/"):
        out.append(p + "index.html")
    else:
        out.append(p)
        out.append(p + ".html")
        out.append(p + "/index.html")
        if "/" in p:
            head, _, tail = p.rpartition("/")
            out.append(f"{head}/{tail}.html")
    return out


def main() -> int:
    sitemap = SITEMAP if SITEMAP.exists() else SITEMAP_FIXTURE
    if not sitemap.exists():
        sys.exit("缺少 sitemap.xml（recon/ 或 tools/fixtures/ 二选一）")
    if not PUBLIC.exists():
        sys.exit("public/ 不存在，先跑 hugo 构建")

    locs = re.findall(r"<loc>([^<]+)</loc>", sitemap.read_text(encoding="utf-8"))
    paths = [re.sub(r"^https?://[^/]+", "", u) or "/" for u in locs]

    missing, hit = [], 0
    for path in paths:
        for cand in candidates(path):
            if (PUBLIC / cand).is_file():
                hit += 1
                break
        else:
            missing.append(path)

    # 产物里不该再有指向原站的内容链接（canonical / alias 跳转是模板自引用，不算）
    old_link = re.compile(r'<(?:a|img)[^>]+(?:href|src)="https?://(?:www\.)?wowotech\.net', re.I)
    stale = []
    for f in PUBLIC.rglob("*.html"):
        for m in old_link.finditer(f.read_text(encoding="utf-8", errors="replace")):
            stale.append((f.relative_to(PUBLIC).as_posix(), m.group(0)[:80]))

    real_missing = [p for p in missing if p not in KNOWN_DEAD]
    lines = [f"原站 sitemap 地址 {len(paths)} 个：命中 {hit}，"
             f"缺失 {len(missing)}（其中 {len(missing) - len(real_missing)} 个原站本身就是 404）",
             f"命中率 {hit / len(paths):.2%}",
             f"指向原站的内容链接：{len(stale)} 处" + ("" if not stale else "（应修复）"),
             ""]
    if stale:
        lines[3:3] = [f"  {w}  {u}" for w, u in stale[:20]]

    # 名称只差大小写的文件在 Windows/macOS 上会互相覆盖（如 PELT.html 与 pelt.html）。
    # 部署在 Linux 上没问题，但本地构建会少一个，这里点出来避免误判。
    from collections import Counter
    resolved = Counter()
    for path in paths:
        for cand in candidates(path):
            if (PUBLIC / cand).is_file():
                resolved[cand.lower()] += 1
                break
    clashes = [k for k, v in resolved.items() if v > 1]
    if clashes:
        lines[2:2] = [f"提示：{len(clashes)} 组地址在大小写不敏感的文件系统上会落到同一个文件：",
                      *[f"  {c}" for c in clashes[:5]], ""]
    lines += missing
    (ROOT / "recon" / "linkcheck.txt").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[:2]))
    if real_missing:
        print("意外缺失：", ", ".join(real_missing[:10]))
    if stale:
        print(f"仍指向原站的内容链接 {len(stale)} 处，例如：{stale[0][0]} {stale[0][1]}")
    return 0 if not real_missing and not stale else 1


if __name__ == "__main__":
    raise SystemExit(main())
