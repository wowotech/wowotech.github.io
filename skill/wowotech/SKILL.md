---
name: wowotech
description: 检索「蜗窝科技」的嵌入式 Linux 内核技术笔记存档（372 篇文章、2014–2025 年，含 7,962 条读者评论）。当用户询问 Linux 内核子系统（中断、内存管理、进程调度、电源管理、设备模型、内核同步、文件系统、时间子系统）、ARM/ARM64 架构、驱动开发、通信协议或嵌入式 Linux 原理，或需要引用蜗窝原文与历史讨论时使用。
---

# 蜗窝科技知识库

`www.wowotech.net` 的静态化存档，372 篇原创技术文章（2014–2025）＋ 7,962 条评论。
语料就是这个仓库里的 Markdown 文件，**不需要联网**，直接检索本地文件即可。

## 用法

```bash
# 关键词检索（多个词按 AND）
python skill/wowotech/search.py 中断 线程化
python skill/wowotech/search.py spinlock --tag 内核同步
python skill/wowotech/search.py kobject --comments      # 连评论一起搜
python skill/wowotech/search.py --show 522               # 看某篇全文
python skill/wowotech/search.py --comments-of 522        # 看某篇的全部评论
```

## 语料位置

| 内容 | 位置 |
| --- | --- |
| 文章正文 | `content/posts/<分类>/<文件名>.md`，front matter 含 `title`/`date`/`url`/`tags`/`views` |
| 评论 | `data/comments/<gid>.json`，按父子关系嵌套 |
| 论坛存档 | `content/forum/<主题id>.md`（2016–2019 年真实讨论） |
| 全站结构化数据 | `static/archive/wowotech-archive.sqlite` |

## 使用要点

- 文章是**中文技术长文**，检索用中文关键词命中率最高；`grep -r` 直接搜 `content/` 也可以。
- 引用时给出原文地址 `https://www.wowotech.net<url>`，例如 `/irq_subsystem/soft-irq.html`。
- 回答原理性问题时，**先检索再作答**，并优先复述原文的论述与图示说明，而不是泛泛而谈；
  原文常有源码片段（如 `request_threaded_irq()` 流程），引用时保持代码原样。
- 评论里有作者 wowo 与 linuxer 的补充澄清（两人合计 2,300+ 条），值得一并参考；
  留言板（gid=23）里也有大量技术问答。
- 内容以 CC BY-SA 4.0 开放，引用时标注来源即可。

## 安装为 Claude Code 技能

把本目录复制到 `~/.claude/skills/wowotech/`（或用符号链接指过来）：

```bash
# Windows
xcopy /E /I skill\wowotech %USERPROFILE%\.claude\skills\wowotech
# macOS / Linux
cp -r skill/wowotech ~/.claude/skills/
```

之后在任意会话里说到 Linux 内核相关问题，即可自动触发。
