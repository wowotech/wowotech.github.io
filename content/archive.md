---
title: "全站数据存档"
url: "/archive/"
---

这里存放原站 `www.wowotech.net` 的完整结构化数据，作为本站之外的第二种存在形式：
即使哪天这个站点也不再维护，任何人都可以从这里拿走全部内容，自行重建或镜像。

## 下载

- [wowotech-archive.sqlite](/archive/wowotech-archive.sqlite) —— 单文件 SQLite 数据库，
  含文章正文、评论、讨论区主题与帖子、成员名录、分类、标签、附件索引。
  已去除邮箱、IP 等个人信息。

## 表结构

| 表 | 内容 |
| --- | --- |
| `posts` | 372 篇文章与页面（含正文 HTML 原文） |
| `comments` | 7,908 条评论，保留父子关系与时间 |
| `forum_topics` / `forum_posts` | 原讨论区 163 个真实主题、792 帖 |
| `forum_users` | 注册成员（用户名、帖数、注册与到访时间） |
| `blog_users` | 原博客注册用户 |
| `categories` / `tags` / `attachments` | 分类、标签与附件索引 |

## 许可

内容版权归原作者所有，采用 [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/deed.zh)
协议开放，欢迎任何形式的镜像与再发布。
