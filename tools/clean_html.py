"""把 emlog 里 Word 粘贴风格的 HTML 清洗成可读 Markdown。

源正文的特征（来自 2014-2016 年从 Word/浏览器粘贴）：
- 满屏 <span style="line-height:1.5"> 包裹、<span lang="EN-US"> 标注西文
- <o:p>、<v:shapetype>、<o:oleobject>、<!--[if gte mso 9]> 等 Office/VML 垃圾
- 用 &nbsp; 做中文首行缩进、用空段落占位
- 标题用 <strong><span style="font-size:16px"> 而非 <h2>
- 代码一部分是 <pre>，一部分是黑底白字的内联 span
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup, Comment
from markdownify import MarkdownConverter

# 需要整块丢弃的 Office / VML / 脚本类标签
JUNK_NAMES = {
    "o:p", "o:lock", "o:oleobject", "o:shapelayout", "o:shapedefaults",
    "v:shapetype", "v:shape", "v:stroke", "v:formulas", "v:f", "v:path",
    "v:imagedata", "v:line", "v:rect", "v:group", "v:oval",
    "w:worddocument", "w:view", "w:zoom", "w:compat", "w:punctuationkerning",
    "xml", "script", "style", "meta", "link", "iframe", "form", "input", "button",
}

# 正文里出现的、属于源码/命令行的高亮样式
CODE_STYLE_HINTS = ("background-color:#000000", "background-color:black", "font-family:monospace",
                    "font-family:courier", "font-family:consolas")

_FONT_SIZE_RE = re.compile(r"font-size\s*:\s*(\d+(?:\.\d+)?)\s*(px|pt)", re.I)
_WS_RE = re.compile(r"[ \t ]+")


class _MD(MarkdownConverter):
    """标题式 Markdown，保留行内 HTML（图片对齐、代码高亮会用到）。"""

    def convert_pre(self, el, text, parent_tags=None, **kwargs):
        lang = ""
        code = el.find("code")
        if code:
            for cls in (code.get("class") or []):
                if isinstance(cls, str) and cls.startswith("language-"):
                    lang = cls[len("language-"):]
            text = code.get_text()
        else:
            text = el.get_text()
        text = text.strip("\n")
        return f"\n\n```{lang}\n{text}\n```\n\n"

    def convert_br(self, el, text, parent_tags=None, **kwargs):
        return "  \n"


def _is_junk(tag) -> bool:
    name = (tag.name or "").lower()
    if name in JUNK_NAMES:
        return True
    return ":" in name and name.split(":", 1)[0] in {"o", "v", "w", "st1", "x"}


def _font_size(tag) -> float:
    """取标签自身或其后代里最大的 font-size（px，pt 按 1pt≈1.33px 折算）。"""
    best = 0.0
    for el in [tag, *tag.find_all(True)]:
        style = el.get("style") or ""
        m = _FONT_SIZE_RE.search(style)
        if m:
            size = float(m.group(1))
            best = max(best, size * 1.33 if m.group(2).lower() == "pt" else size)
    return best


def _mark_code(soup: BeautifulSoup) -> None:
    for span in soup.find_all("span"):
        style = (span.get("style") or "").replace(" ", "").lower()
        if any(hint.replace(" ", "") in style for hint in CODE_STYLE_HINTS):
            span.name = "code"
            span.attrs = {}


def _promote_headings(soup: BeautifulSoup) -> None:
    """整段被加粗且字号偏大、长度较短的段落当成二级标题。"""
    for p in soup.find_all("p"):
        strong = p.find(["strong", "b"])
        if not strong:
            continue
        text = p.get_text(strip=True)
        if not text or len(text) > 80:
            continue
        bold_text = strong.get_text(strip=True)
        if len(bold_text) < len(text) * 0.9:
            continue
        if _font_size(strong) >= 15:
            h2 = soup.new_tag("h2")
            h2.string = text
            p.replace_with(h2)


def _normalize(soup: BeautifulSoup) -> None:
    for span in soup.find_all("span"):
        span.unwrap()

    for tag in soup.find_all(True):
        if tag.name == "a":
            tag.attrs = {k: v for k, v in tag.attrs.items() if k in ("href", "title")}
        elif tag.name == "img":
            tag.attrs = {k: v for k, v in tag.attrs.items() if k in ("src", "alt", "title")}
        else:
            tag.attrs = {}

    for tag in soup.find_all(["p", "li", "h1", "h2", "h3", "h4", "div", "td", "th"]):
        # 首行缩进用的 &nbsp; 去掉，段中多余的空白折叠
        for text_node in tag.find_all(string=True):
            if text_node.parent.name in ("pre", "code"):
                continue
            collapsed = _WS_RE.sub(" ", str(text_node))
            if text_node.parent.name in ("p", "li", "h1", "h2", "h3", "h4", "td", "th"):
                collapsed = collapsed.strip() if not collapsed.strip() else collapsed
            if collapsed != str(text_node):
                text_node.replace_with(collapsed)

    for tag in soup.find_all(["p", "div", "li", "h1", "h2", "h3", "h4"]):
        if not tag.get_text(strip=True) and not tag.find(["img", "br"]):
            tag.decompose()

    # 图片外面那层“点击看原图”的链接：href 指向同一张图时直接去掉
    for a in soup.find_all("a"):
        img = a.find("img")
        if img is None:
            continue
        href = (a.get("href") or "").rstrip("/").split("/")[-1]
        src = (img.get("src") or "").rstrip("/").split("/")[-1]
        if href and src and href.replace("thum-", "") == src.replace("thum-", ""):
            a.unwrap()


def clean(content: str) -> str:
    soup = BeautifulSoup(content or "", "lxml")

    for comment in soup.find_all(string=lambda s: isinstance(s, Comment)):
        comment.extract()
    for tag in soup.find_all(lambda t: _is_junk(t)):
        tag.decompose()

    _mark_code(soup)
    _promote_headings(soup)
    _normalize(soup)

    md = _MD(heading_style="ATX", bullets="-", strong_em_symbol="*").convert_soup(soup)
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip() + "\n"


if __name__ == "__main__":
    import sys
    from pathlib import Path

    src = Path(sys.argv[1])
    print(clean(src.read_text(encoding="utf-8")))
