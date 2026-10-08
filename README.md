# 蜗窝科技 · 静态存档

原 `www.wowotech.net`（emlog 博客 ＋ PunBB 讨论区）的静态化迁移工程。

站点已经不再需要动态后端：文章是 Markdown，评论与论坛帖是冻结的只读存档，
整站由 Hugo 生成，发布在 GitHub Pages 上，托管成本为零。

## 现在长什么样

| 内容 | 数量 | 说明 |
| --- | --- | --- |
| 文章与页面 | 377 | 2014–2025 年的技术笔记，URL 与原站一致 |
| 评论 | 7,962 | 冻结为只读，保留昵称、时间与父子回复关系 |
| 讨论区主题 | 163 | 原 PunBB 论坛 2016–2019 年的真实讨论（792 帖） |
| 分类 / 月度存档 / 标签页 | 24 / 78 / 526 | 原站地址形态全部保留 |
| 侧栏 | 6 个模块 | 站内搜索、功能、最新评论、文章分类、文章存档、友情链接与统计 |
| 附件 | 1,110 | 图片与 PDF，路径沿用 `/content/uploadfile/...` |

**旧链接保留率 1007/1008（99.9%）**，唯一缺失的 `/soft/501.html` 在原站本身就是 404
（未审核文章）。产物里**没有任何指向原站的内容链接**（canonical 等模板自引用除外）。

站内链接另做了一遍复审：原站路由忽略分类前缀、也不要求 `.html` 后缀，
照搬过来会有一批点不到的链接。现在这类链接已从 **285 处降到 12 处**，
且这 12 处经核对在原站本身就是 404。

两条验收命令：

```bash
python tools/check_links.py          # 旧地址覆盖 + 产物里是否还有跳回原站的链接
python tools/normalize_links.py --check   # 语料里是否还有指向原站的绝对地址（CI 门禁）
```

站内搜索是纯前端的：索引为 `static/search-index.json`，页面在 `/search/`。
侧栏数据在 `data/nav.json`（分类、存档、友情链接、统计）。

## 目录

```
content/        文章、页面、论坛主题（Markdown，唯一事实来源）
  posts/        文章，按分类分目录
  forum/        讨论区只读存档
  _gen/         分类页 / 月度存档 / 标签页（脚本生成）
data/           评论（每篇一个 JSON）、侧栏数据、站点信息、旧地址与 slug 映射
layouts/        Hugo 模板
static/         CSS、搜索索引、附件图片、可下载的数据存档
tools/          抓取、转换、构建、校验脚本
config/         主机与数据库凭据（config.ini 不入库）
recon/          原始 dump 与探查报告（不入库：含邮箱/IP、体积大）
docs/           迁移方法与同步流程说明
```

## 重建站点

```bash
# 1. 取 Hugo（扩展版，单文件，不入库）
mkdir -p tools/bin && cd tools/bin
curl -sSL -o hugo.tar.gz https://github.com/gohugoio/hugo/releases/download/v0.167.0/hugo_extended_0.167.0_windows-amd64.zip
# Linux/macOS 换成 ..._linux-amd64.tar.gz / ..._darwin-universal.tar.gz 并解压
cd ../..

# 2. 构建（语料已在仓库里，无需联网）
./tools/bin/hugo server        # 本地预览 http://localhost:1313

# 3. 从原站同步最新内容（详见 docs/）
python tools/sync.py
```

Python 依赖：`pip install markdownify beautifulsoup4 lxml markdown`

## 数据存档

`static/archive/wowotech-archive.sqlite` 是全站结构化数据（文章正文、评论、论坛帖、
成员名录、分类标签），可单独下载、离线查询。公开版本已去除邮箱与 IP；
含个人信息的完整版不入库，保存在本地 `../wowotech-archive-private/`。

## 许可

内容版权归原作者所有，以 [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/deed.zh)
开放，欢迎镜像与再发布。
