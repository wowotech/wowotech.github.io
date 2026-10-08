"""MySQL dump 解析器（无第三方依赖）。

支持 `INSERT INTO t VALUES(...),(...);` 与 `INSERT INTO t (a,b) VALUES ...`，
处理反斜杠转义、单引号转义、NULL 与数值字面量。用于把 emlog/PunBB 的 dump
读成 Python 行数据，供后续转 Markdown、建静态站使用。
"""
from __future__ import annotations

import re
from pathlib import Path

_ESCAPES = {
    "0": "\0", "b": "\b", "n": "\n", "r": "\r", "t": "\t",
    "Z": "\x1a", "\\": "\\", "'": "'", '"': '"', "%": "%", "_": "_",
}

_INSERT_RE = re.compile(
    r"INSERT\s+INTO\s+`?([A-Za-z0-9_]+)`?\s*(\([^)]*\))?\s*VALUES\s*",
    re.I,
)


def _unescape(raw: str) -> str:
    out, i, n = [], 0, len(raw)
    while i < n:
        ch = raw[i]
        if ch == "\\" and i + 1 < n:
            nxt = raw[i + 1]
            out.append(_ESCAPES.get(nxt, nxt))
            i += 2
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def _split_tuples(body: str):
    """把 VALUES 之后的文本按顶层元组切开。"""
    rows, cur, depth, in_str, esc = [], [], 0, False, False
    for ch in body:
        if in_str:
            cur.append(ch)
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == "'":
                in_str = False
            continue
        if ch == "'":
            in_str = True
            cur.append(ch)
        elif ch == "(":
            depth += 1
            if depth == 1:
                cur = []
            else:
                cur.append(ch)
        elif ch == ")":
            depth -= 1
            if depth == 0:
                rows.append("".join(cur))
            else:
                cur.append(ch)
        elif depth == 0 and ch == ";":
            break
        elif depth > 0:
            cur.append(ch)
    return rows


def _split_values(tup: str) -> list:
    vals, cur, in_str, esc = [], [], False, False
    for ch in tup:
        if in_str:
            cur.append(ch)
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == "'":
                in_str = False
            continue
        if ch == "'":
            in_str = True
            cur.append(ch)
        elif ch == ",":
            vals.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    vals.append("".join(cur).strip())

    out = []
    for v in vals:
        if v.startswith("'") and v.endswith("'") and len(v) >= 2:
            out.append(_unescape(v[1:-1]))
        elif v.upper() == "NULL":
            out.append(None)
        else:
            out.append(v)
    return out


def parse(path: str | Path, want: set[str] | None = None) -> dict[str, list[list]]:
    """解析 dump，返回 {表名: [行, ...]}；want 可限定只解析部分表。"""
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    data: dict[str, list[list]] = {}
    pos = 0
    for m in _INSERT_RE.finditer(text):
        table = m.group(1)
        if want and table not in want:
            continue
        body = text[m.end():]
        for tup in _split_tuples(body):
            data.setdefault(table, []).append(_split_values(tup))
        pos = m.end()
    return data


def columns(path: str | Path) -> dict[str, list[str]]:
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    out = {}
    for m in re.finditer(r"CREATE TABLE\s+`?([A-Za-z0-9_]+)`?\s*\((.*?)\n\)", text, re.S):
        out[m.group(1)] = re.findall(r"^\s*`([^`]+)`", m.group(2), re.M)
    return out


def records(path: str | Path, table: str) -> list[dict]:
    """按 dump 中 INSERT 的列顺序 + CREATE TABLE 列名组合成 dict。"""
    cols = columns(path).get(table, [])
    rows = parse(path, {table}).get(table, [])
    if not cols:
        return [dict(enumerate(r)) for r in rows]
    return [dict(zip(cols, r)) for r in rows]


if __name__ == "__main__":
    import sys

    src = sys.argv[1]
    info = columns(src)
    data = parse(src)
    for t in sorted(set(info) | set(data)):
        print(f"{t:26s} cols={len(info.get(t, [])):3d} rows={len(data.get(t, [])):6d}")
