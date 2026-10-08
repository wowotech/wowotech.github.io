"""统一处理站内链接：把指向原站的地址改成本站路径，并修正「点不到」的相对链接。

为什么需要它：正文、论坛存档、评论里散落着大量指向 www.wowotech.net 的绝对地址，
以及分类写错、缺 .html 后缀、旧动态形式的站内地址。逐处修补治不了根，
所以把所有链接规则集中到这一个文件，作为固定工序跟在 convert 之后、构建之前跑。

处理对象：
  content/**/*.md        文章、页面、论坛存档（跳过围栏代码与行内代码）
  data/comments/*.json   评论正文 text 与评论者主页 site

改写规则：
  1) 绝对地址去域名
     · 本站域名（含主机商别名 gotoip11/gotoftp11）→ 去掉协议与主机
     · 图片 CDN 域名（www.wowotech.net.img.800cdn.com 之类）→ 取路径并登记为待下载附件
     · /?post=N → 用 data/urlmap.json 还原成规范地址
     · 非本站域名一律不动（github.com/wowotechX 这类要保住）
  2) 站内相对地址的修正（原站路由比较宽松，照搬会点不到）
     · 补 .html 后缀（原站 /support_list 与 /support_list.html 都能开）
     · 忽略分类前缀按 slug 找回：原站路由不看分类，作者当年把分类写成
       /linux_kenrel/（这个别名本身就是原站里的拼写错误）也能打开，
       我们按文件基名反查真实地址（如 /linux_kenrel/bus.html → /device_model/bus.html）
     · 旧动态形式：/forum/viewtopic.php?id=N → /forum/N.html；viewforum.php → /forum/
     · org-mode 导出的目录锚点：/admin/#orgxxxx → #orgxxxx（页内锚点）
     · 百分号编码的地址按解码后的路径判断是否存在

看不到的情况会记进 recon/linknorm_report.txt，方便人工确认。

用法：
  python tools/normalize_links.py           # 就地改写
  python tools/normalize_links.py --check   # 只检查不写入；仍有指向原站的链接则退出码 1
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
COMMENTS = ROOT / "data" / "comments"
URLMAP = ROOT / "data" / "urlmap.json"
ASSET_MANIFEST = ROOT / "recon" / "assets.txt"
REPORT = ROOT / "recon" / "linknorm_report.txt"

# 本站域名（含主机商给的源站别名，以防有链接写成了那个）
SITE_HOSTS = {
    "www.wowotech.net", "wowotech.net",
    "wowotech.gotoip11.com", "wowotech.gotoftp11.com",
}
# 图片 CDN：路径部分就是原站路径，直接取用
ASSET_HOST_RE = re.compile(r"^(?:[\w-]+\.)*wowotech[\w.-]*\.(?:800cdn\.com|addlink\.cn)$", re.I)
# 主机名之后只吃 ASCII 里合法的 URL 字符：中文正文紧跟地址时通常没有空格，
# 若用 [^\s] 会把后面的中文一起吞进来（"http://…/a.html本文描述…"）
URL_RE = re.compile(r"(https?)://([^\s\)\]\"'<>/]+)([A-Za-z0-9\-._~:/?#@!$&*+,;=%\\]*)", re.I)
# 句末标点常被 URL 正则吞掉，匹配后要还回去
TRAILING_PUNCT = ",.;:!?*"
FENCE_RE = re.compile(r"(^|\n)(```.*?```|~~~.*?~~~)", re.S)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
# 站内相对链接：markdown 目标与 HTML 属性两种写法
MD_TARGET_RE = re.compile(r"\]\(\s*(/[^)\s]*)")
HTML_ATTR_RE = re.compile(r'((?:href|src)=")(/[^"\s]*)"')
# 评论是纯文本，只保守处理「带 .html」的和已知的无扩展名页面
BARE_HTML_PATH_RE = re.compile(
    r"(^|[^A-Za-z0-9_\-./:%=&?#\"'<>=])"
    r"((?:/[A-Za-z0-9_\-]+)+/[A-Za-z0-9_\-]+\.html)")
# 正文里引用的站内资源（含作者当年上传到 /admin/ 目录的图），要确保本地有一份
ASSET_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".ico",
              ".pdf", ".zip", ".rar", ".7z", ".tar", ".gz", ".mp4", ".mp3"}
LEGACY_TOPIC_RE = re.compile(r"^/forum/viewtopic(?:\.php)?(?:\?id=(\d+))?")
LEGACY_FORUM_RE = re.compile(r"^/forum/viewforum(?:\.php)?")
# org-mode / emlog 后台导出的产物：本意是「本页内的锚点」，但链接写成了 /admin/#xxx
ADMIN_ANCHOR_RE = re.compile(r"^/admin/(#.*)$")
# WordPress 式后缀：/xxx.html/comment-page-2、/xxx/feed 之类，指的还是那篇文章
WP_SUFFIX_RE = re.compile(r"^(.*?\.html)/(?:comment-page-\d+|feed|trackback)/?$")

# 一定有、但不在 front matter 里的地址
EXTRA_KNOWN = {"/", "/index.html", "/forum/", "/forum/index.html", "/archive/",
               "/archive/index.html", "/404.html", "/llms.txt", "/robots.txt",
               "/sitemap.xml", "/index.xml"}


def load_known_urls() -> set[str]:
    """站点上确实存在的路径集合：生成页的 url ＋ 静态目录里的实际文件。"""
    known: set[str] = set(EXTRA_KNOWN)
    for f in CONTENT.rglob("*.md"):
        m = re.search(r'^url: "(.*?)"', f.read_text(encoding="utf-8"), re.M)
        if m:
            url = m.group(1)
            known.add(url)
            known.add(url.rstrip("/") + "/index.html")     # /forum/ 这类段落首页
    static = ROOT / "static"
    for f in static.rglob("*"):
        if f.is_file():
            known.add("/" + f.relative_to(static).as_posix())
    return known


def load_urlmap() -> dict[str, str]:
    if URLMAP.exists():
        return json.loads(URLMAP.read_text(encoding="utf-8"))
    return {}


def build_slugmap(known: set[str]) -> dict[str, list[str]]:
    """基名 → 候选地址列表。原站路由忽略分类前缀，靠这张表把写错分类的链接找回。

    数字基名会在博客（文章 gid）与论坛（主题号）两个命名空间里重名，
    所以保留候选列表，由调用方按链接自身的路径前缀来取舍，而不是直接丢弃。
    """
    buckets: dict[str, set[str]] = {}
    for url in known:
        if not url.endswith((".html", "/")) or url.endswith("/index.html"):
            continue
        base = url.rstrip("/").rsplit("/", 1)[-1]
        slug = re.sub(r"\.html$", "", base).lower()
        if slug:
            buckets.setdefault(slug, set()).add(url)
    return {slug: sorted(urls) for slug, urls in buckets.items()}


class Normalizer:
    def __init__(self, known: set[str], urlmap: dict[str, str]):
        self.known = known
        self.urlmap = urlmap
        self.slugmap = build_slugmap(known)
        self.stats: Counter = Counter()
        self.unresolved: list[tuple[str, str]] = []
        self.fixed_relative: list[tuple[str, str, str]] = []
        self.new_assets: set[str] = set()

    # ---- 存在性判断 -----------------------------------------------------
    def exists(self, path: str) -> bool:
        """严格判断：只有这个地址本身（含百分号解码、目录首页）存在才算存在。

        注意不能把 `path + ".html"` 也算进来——否则 /support_list 会被当成
        「已经没问题」，补后缀的规则永远不触发。
        """
        if path in self.known:
            return True
        decoded = urllib.parse.unquote(path)
        if decoded in self.known:
            return True
        return path.endswith("/") and path + "index.html" in self.known

    # ---- 站内相对地址的修正 ---------------------------------------------
    def fix_relative(self, path: str, where: str) -> str:
        frag = ""
        if "#" in path:
            path, _, f = path.partition("#")
            frag = "#" + f
        path = path.replace("\\_", "_").replace("\\-", "-")
        if not path or self.exists(path) or (not path.endswith("/") and self.exists(path + "/")):
            return path + frag

        # org-mode 导出的目录锚点：本意是页内锚点
        m = ADMIN_ANCHOR_RE.match(path + frag)
        if m:
            self.stats["/admin/#x 改回页内锚点"] += 1
            return m.group(1)

        # WordPress 式后缀：剥掉尾巴指回原文章
        m = WP_SUFFIX_RE.match(path)
        if m:
            base = m.group(1)
            if self.exists(base):
                self.stats["剥掉 /comment-page-N 之类后缀"] += 1
                return base + frag

        # 老站的 RSS/订阅入口
        if path in ("/rss.php", "/rss", "/feed", "/feed.php", "/atom.xml"):
            self.stats["老站 RSS 地址指向新 feed"] += 1
            return "/index.xml"

        # 旧动态论坛地址
        m = LEGACY_TOPIC_RE.match(path)
        if m:
            if m.group(1) and f"/forum/{m.group(1)}.html" in self.known:
                self.stats["旧动态 /forum/viewtopic.php?id=N 指向存档主题"] += 1
                return f"/forum/{m.group(1)}.html"
            self.stats["旧动态论坛地址改为存档首页"] += 1
            return "/forum/" + frag
        if LEGACY_FORUM_RE.match(path):
            self.stats["旧动态版块地址改为存档首页"] += 1
            return "/forum/" + frag

        # 补 .html：原站 /support_list 与 /support_list.html 都通
        if "." not in path.rsplit("/", 1)[-1] and path + ".html" in self.known:
            self.stats["补 .html 后缀"] += 1
            return path + ".html" + frag

        # 按 slug 找回（原站不看分类前缀）
        slug = re.sub(r"\.html$", "", path.rstrip("/").rsplit("/", 1)[-1]).lower()
        target = self._pick_slug(slug, path)
        if target:
            self.stats["按 slug 找回（分类前缀写错）"] += 1
            self.fixed_relative.append((where, path, target))
            return target + frag

        # 站内资源（图片等）：登记下载，路径保持原样就能继续用
        if Path(path).suffix.lower() in ASSET_EXTS:
            self.new_assets.add(path)
            self.stats["站内资源登记下载"] += 1
            return path + frag

        self.stats["站内链接确实不存在（保持原样）"] += 1
        self.unresolved.append((where, path))
        return path + frag

    def _pick_slug(self, slug: str, source_path: str) -> str | None:
        """同名候选里挑一个：来源在 /forum/ 下就优先论坛主题，否则优先文章。"""
        cands = self.slugmap.get(slug)
        if not cands:
            return None
        if len(cands) == 1:
            return cands[0]
        forum = [c for c in cands if c.startswith("/forum/")]
        posts = [c for c in cands if not c.startswith("/forum/")]
        if source_path.startswith("/forum/") or source_path.startswith("viewtopic"):
            return forum[0] if len(forum) == 1 else None
        return posts[0] if len(posts) == 1 else None

    # ---- 绝对地址的改写 -------------------------------------------------
    def one(self, full: str, host: str, rest: str, where: str) -> str:
        host = host.lower()
        path_and_query, _, frag = rest.partition("#")
        path, _, query = path_and_query.partition("?")

        if ASSET_HOST_RE.match(host):
            asset = "/" + path.lstrip("/")
            if asset not in self.known:
                self.new_assets.add(asset)
            self.stats["图片 CDN 改为本地路径"] += 1
            return asset + (f"#{frag}" if frag else "")

        if host not in SITE_HOSTS:
            if "wowotech" in host:
                self.stats["含 wowotech 的陌生域名（保持原样）"] += 1
            return full

        if query.startswith("post="):
            gid = query.split("=", 1)[1].split("&")[0]
            if gid in self.urlmap:
                self.stats["?post=N 还原为文章地址"] += 1
                return self.urlmap[gid] + (f"#{frag}" if frag else "")
            self.stats["?post=N 无法还原"] += 1
            return "/" + (f"#{frag}" if frag else "")

        if path in ("", "/"):
            self.stats["本站根地址改为 /"] += 1
            return "/" + (f"#{frag}" if frag else "")
        return self.fix_relative(path + (f"#{frag}" if frag else ""), where)

    # ---- 文本处理 -------------------------------------------------------
    def text(self, s: str, where: str) -> str:
        def sub(m: re.Match) -> str:
            rest = m.group(3)
            stripped = rest.rstrip(TRAILING_PUNCT)      # 句末的 , . ; : ! ? 要还回去
            tail = rest[len(stripped):]
            return self.one(m.group(0), m.group(2), stripped, where) + tail

        return URL_RE.sub(sub, s)

    def bare_paths(self, s: str, where: str) -> str:
        """评论这类纯文本：只处理「前面不是 URL 字符」的带 .html 站内路径。

        否则会把外站链接的路径部分（https://www.cnblogs.com/xxx/p/123.html 里的
        /xxx/p/123.html）当成本站路径来解析。
        """
        def sub(m: re.Match) -> str:
            head, path = m.group(1), m.group(2)
            if self.exists(path):
                return m.group(0)
            return head + self.fix_relative(path, where)

        return BARE_HTML_PATH_RE.sub(sub, s)

    def markdown(self, s: str, where: str) -> str:
        """跳过围栏代码块和行内代码，避免改坏示例代码。"""
        out, pos = [], 0
        for m in FENCE_RE.finditer(s):
            out.append(self._md_segment(s[pos:m.start(2)], where))
            out.append(m.group(2))          # 代码块原样保留
            pos = m.end(2)
        out.append(self._md_segment(s[pos:], where))
        return "".join(out)

    def _md_segment(self, seg: str, where: str) -> str:
        parts, pos = [], 0
        for m in INLINE_CODE_RE.finditer(seg):
            parts.append(self._md_chunk(seg[pos:m.start()], where))
            parts.append(m.group(0))        # 行内代码原样保留
            pos = m.end()
        parts.append(self._md_chunk(seg[pos:], where))
        return "".join(parts)

    def _md_chunk(self, chunk: str, where: str) -> str:
        chunk = self.text(chunk, where)                     # 先处理绝对地址
        chunk = MD_TARGET_RE.sub(
            lambda m: "](" + self.fix_relative(m.group(1), where), chunk)
        return HTML_ATTR_RE.sub(
            lambda m: m.group(1) + self.fix_relative(m.group(2), where) + '"', chunk)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只检查不写入；有指向原站的链接则退出码 1")
    return run(ap.parse_args().check)


def run(check: bool = False) -> int:
    """就地规范化（或只检查）。convert.py 生成语料后会自动调用它，
    避免「重新生成＝把链接打回原形」这种陷阱。"""
    nz = Normalizer(load_known_urls(), load_urlmap())
    changed_files = 0

    for f in sorted(CONTENT.rglob("*.md")):
        src = f.read_text(encoding="utf-8")
        dst = nz.markdown(src, f.relative_to(ROOT).as_posix())
        if dst != src:
            changed_files += 1
            if not check:
                f.write_text(dst, encoding="utf-8")

    comments_changed = 0
    for f in sorted(COMMENTS.glob("*.json")):
        items = json.loads(f.read_text(encoding="utf-8"))
        dirty = False
        for c in items:
            site = (c.get("site") or "").strip()
            if site and re.match(r"^https?://(?:www\.)?wowotech\.net/?$", site, re.I):
                c["site"] = ""              # 评论者「主页」指向本站首页，纯噪音，去掉
                nz.stats["评论主页字段是本站首页，清空"] += 1
                dirty = True
            elif site:
                new = nz.text(site, f"{f.name} site")
                if new != site:
                    c["site"] = new
                    dirty = True
            text = c.get("text") or ""
            new = nz.bare_paths(nz.text(text, f"{f.name} text"), f"{f.name} text")
            if new != text:
                c["text"] = new
                dirty = True
        if dirty:
            comments_changed += 1
            if not check:
                f.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")

    if nz.new_assets and not check:
        existing = set()
        if ASSET_MANIFEST.exists():
            existing = {l.strip() for l in ASSET_MANIFEST.read_text(encoding="utf-8").splitlines() if l.strip()}
        merged = sorted(existing | nz.new_assets)
        if merged != sorted(existing):
            # 整体重写而不是 append：清单若缺结尾换行，append 会把两行粘成一行
            ASSET_MANIFEST.write_text("\n".join(merged) + "\n", encoding="utf-8")

    lines = [f"改写文件：content {changed_files} 个，评论 {comments_changed} 个",
             f"新登记待下载附件：{len(nz.new_assets)} 个", "", "=== 规则命中次数 ==="]
    lines += [f"{v:6d}  {k}" for k, v in nz.stats.most_common()]
    if nz.fixed_relative:
        lines += ["", f"=== 按 slug 找回的链接 {len(nz.fixed_relative)} 处（原文分类前缀写错）==="]
        lines += [f"{w}\t{p} → {t}" for w, p, t in nz.fixed_relative[:60]]
    if nz.unresolved:
        lines += ["", f"=== 站内确实不存在的链接 {len(nz.unresolved)} 处 ==="]
        lines += [f"{w}\t{p}" for w, p in nz.unresolved[:60]]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")

    print(lines[0])
    print(lines[1])
    for k, v in nz.stats.most_common():
        print(f"{v:6d}  {k}")
    if nz.unresolved:
        print(f"\n仍有 {len(nz.unresolved)} 处站内链接指向不存在的地址，详见 {REPORT.name}")

    if check:
        left = 0
        for f in CONTENT.rglob("*.md"):
            left += len(re.findall(r"https?://(?:www\.)?wowotech\.net", f.read_text(encoding="utf-8"), re.I))
        for f in COMMENTS.glob("*.json"):
            left += len(re.findall(r"https?://(?:www\.)?wowotech\.net",
                                   f.read_text(encoding="utf-8"), re.I))
        if left:
            print(f"\n检查未通过：仍有 {left} 处指向原站的链接（详见 {REPORT.name}）")
            return 1
        print("\n检查通过：没有指向原站的链接")
    return 0


if __name__ == "__main__":
    sys.exit(main())
