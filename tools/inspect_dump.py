"""快速探查 SQL dump：表清单、行数、字段与正文格式样例。

用法: python tools/inspect_dump.py <dump.sql> [报告输出路径]
"""
import re
import sys
from collections import Counter
from pathlib import Path

src = Path(sys.argv[1] if len(sys.argv) > 1 else "recon/emlog_20250207.sql")
out = Path(sys.argv[2] if len(sys.argv) > 2 else "recon/report.txt")
text = src.read_text(encoding="utf-8", errors="replace")

lines = []
add = lines.append

add(f"# 探查报告: {src.name}")
add(f"文件大小: {len(text):,} 字符\n")

add("## 表清单与 INSERT 行数")
tables = re.findall(r"CREATE TABLE\s+`?([A-Za-z0-9_]+)`?", text)
ins = Counter(re.findall(r"INSERT INTO\s+`?([A-Za-z0-9_]+)`?", text))
for t in tables:
    add(f"  {t:28s} rows={ins.get(t, 0)}")


def show_columns(table):
    m = re.search(rf"CREATE TABLE\s+`?{table}`?\s*\((.*?)\n\)", text, re.S)
    if not m:
        return
    cols = re.findall(r"^\s*`([^`]+)`", m.group(1), re.M)
    add(f"\n### {table} 字段\n  " + ", ".join(cols))


for t in ("emlog_blog", "emlog_comment", "emlog_user", "emlog_sort", "emlog_twitter"):
    show_columns(t)


def sample(table, n=1, width=700):
    add(f"\n## {table} 样例（{n} 条，各截 {width} 字符）")
    pat = re.compile(rf"INSERT INTO\s+`?{table}`?\s+VALUES\((.*?)\);\s*$", re.M | re.S)
    for i, m in enumerate(pat.finditer(text)):
        if i >= n:
            break
        body = m.group(1)
        add(f"\n--- 第 {i + 1} 条 ---")
        add(body[:width])


sample("emlog_blog", 2)
sample("emlog_comment", 2)
sample("emlog_user", 3)
sample("emlog_twitter", 1)

out.write_text("\n".join(lines), encoding="utf-8")
print(f"report -> {out} ({len(lines)} lines)")
