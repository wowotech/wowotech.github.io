"""PunBB 论坛正文（BBCode）转 Markdown。

论坛帖子是 BBCode 而非 HTML，且会被原样嵌进页面，所以先做 HTML 转义再解析标记，
避免老帖里的 <script> 之类的东西被当成标签执行。
"""
from __future__ import annotations

import html
import re

_SMILE = re.compile(r"(?<=[\s(])(?::\)|:D|;\)|:P|:\(|:o|:shock:|:lol:|:roll:|:?\))")
_QUOTE_OPEN = re.compile(r"\[quote(?:=&quot;([^&]*?)&quot;|=([^\]]+))?\]", re.I)
_BLOCK = {
    "b": "**", "i": "*", "u": "", "s": "~~", "color": "", "size": "", "font": "",
    "center": "", "left": "", "right": "", "sup": "", "sub": "",
}


def to_markdown(text: str) -> str:
    if not text:
        return ""
    s = html.escape(text, quote=False)

    s = re.sub(r"\[code\](.*?)\[/code\]", lambda m: f"\n```\n{html.unescape(m.group(1))}\n```\n", s, flags=re.S | re.I)

    for tag, md in _BLOCK.items():
        if md:
            s = re.sub(rf"\[{tag}\](.*?)\[/{tag}\]", rf"{md}\1{md}", s, flags=re.S | re.I)
        else:
            s = re.sub(rf"\[/?{tag}(?:=[^\]]*)?\]", "", s, flags=re.I)

    s = _QUOTE_OPEN.sub(lambda m: f"\n> **{(m.group(1) or m.group(2) or '')} 写道：**\n> ", s)
    s = re.sub(r"\[/quote\]", "\n\n", s, flags=re.I)

    s = re.sub(r"\[url=(?:&quot;)?([^\]&]+)(?:&quot;)?\](.*?)\[/url\]", r"[\2](\1)", s, flags=re.S | re.I)
    s = re.sub(r"\[url\](.*?)\[/url\]", r"<\1>", s, flags=re.S | re.I)
    s = re.sub(r"\[email\](.*?)\[/email\]", r"<\1>", s, flags=re.I)
    s = re.sub(r"\[img\](.*?)\[/img\]", r"![](\1)", s, flags=re.I)
    s = re.sub(r"\[img=[^\]]*\](.*?)\[/img\]", r"![](\1)", s, flags=re.I)

    s = re.sub(r"\[list(?:=[^\]]*)?\]", "\n", s, flags=re.I)
    s = re.sub(r"\[/list\]", "\n", s, flags=re.I)
    s = re.sub(r"\[\*\]\s*", "\n- ", s, flags=re.I)
    s = re.sub(r"\[/?(?:hr|u|spoiler|noparse|flash|video|table|tr|td|th|tt|mono|acronym|attach|topic|post|forum|user|group|m|h|o|c|p|q|f|e|d|g|s|u)[^\]]*\]", "", s, flags=re.I)

    s = _SMILE.sub("", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()
