"""一条命令完成同步：活库 → 语料 → 静态站。

流程：
  1. 生成随机 token，把 tools/export.php 渲染后经 FTP 上传到站点根目录（临时文件）
  2. 通过 HTTP 拉取活库数据到 recon/live_export.json
  3. 无论成功与否，立即删除服务器上的临时文件
  4. 重新生成语料（活库优先，dump 补齐缺失表）
  5. 补下新增附件，构建静态站

用法：
  python tools/sync.py                 # 完整同步
  python tools/sync.py --offline       # 不碰线上，只用本地 dump 重建
  python tools/sync.py --deploy        # 构建后再 git commit + push（交给 GitHub Actions 发布）
"""
from __future__ import annotations

import argparse
import configparser
import ftplib
import io
import json
import secrets
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HUGO = ROOT / "tools" / "bin" / ("hugo.exe" if sys.platform == "win32" else "hugo")
LIVE_JSON = ROOT / "recon" / "live_export.json"


def load_cfg() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    if not cfg.read(ROOT / "config" / "config.ini", encoding="utf-8"):
        sys.exit("缺少 config/config.ini（可从 config/config.example.ini 复制并填写）")
    return cfg


def step(msg: str) -> None:
    print(f"\n=== {msg} ===", flush=True)


def run(cmd: list[str], **kw) -> None:
    print("$", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True, **kw)


# ------------------------------------------------------------------ 活库拉取

def fetch_live(cfg: configparser.ConfigParser) -> Path | None:
    host = cfg["ftp"]["host"]
    user = cfg["ftp"]["user"]
    password = cfg["ftp"]["password"]
    webroot = cfg["ftp"].get("root", "/wwwroot").rstrip("/")
    # 走源站别名 + Host 头，避开 CDN 的 WAF 限流（CDN 会对我们的批量请求返回 403）
    base = cfg["origin"].get("fetch_url", cfg["origin"]["base_url"]).rstrip("/")
    host_header = cfg["origin"].get("fetch_host", "")

    token = secrets.token_urlsafe(24)
    remote_name = f"_wxsync_{secrets.token_hex(6)}.php"
    php = (ROOT / "tools" / "export.php").read_text(encoding="utf-8").replace("__TOKEN__", token)

    step(f"上传临时导出端点 {webroot}/{remote_name}")
    ftp = ftplib.FTP(host, timeout=90)
    ftp.login(user, password)
    ftp.set_pasv(True)
    try:
        ftp.cwd(webroot)
        ftp.storbinary(f"STOR {remote_name}", io.BytesIO(php.encode("utf-8")))
        step("拉取活库数据")
        url = f"{base}/{remote_name}?k={urllib.parse.quote(token)}"
        headers = {"User-Agent": "wowotech-sync/1.0"}
        if host_header:
            headers["Host"] = host_header
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=600) as resp:
            body = resp.read()
        try:
            data = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            print("  返回的不是 JSON，前 300 字节：", body[:300])
            return None
        tables = data.get("tables") or {}
        counts = {k: len(v) for k, v in tables.items()}
        print(f"  PHP {data.get('php')} · 表：{counts}")
        LIVE_JSON.parent.mkdir(parents=True, exist_ok=True)
        LIVE_JSON.write_bytes(body)
        return LIVE_JSON
    except (ftplib.error_perm, urllib.error.URLError, OSError) as e:
        print(f"  活库拉取失败：{e}")
        return None
    finally:
        # 临时端点必须删掉，不能留在线上
        try:
            ftp.delete(remote_name)
            print(f"  已删除线上临时文件 {remote_name}")
        except Exception as e:  # noqa: BLE001
            print(f"  ！删除 {remote_name} 失败，请手动清理：{e}")
        finally:
            try:
                ftp.quit()
            except Exception:  # noqa: BLE001
                ftp.close()


# ------------------------------------------------------------------ 主流程

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="只用本地 dump，不访问线上")
    ap.add_argument("--skip-assets", action="store_true", help="跳过附件补下")
    ap.add_argument("--skip-build", action="store_true", help="只生成语料，不构建站点")
    ap.add_argument("--deploy", action="store_true", help="构建后 commit + push")
    args = ap.parse_args()

    cfg = load_cfg()
    if args.offline:
        # 离线 = 不联系原站，但仍优先复用上一次的活库导出（比本地 dump 新）
        live = LIVE_JSON if LIVE_JSON.exists() else None
        if live:
            print(f"  离线模式：复用上次的活库导出 {live.name}")
    else:
        # 拉取失败就退回上一次的导出，避免内容退回到 dump 的旧状态
        live = fetch_live(cfg) or (LIVE_JSON if LIVE_JSON.exists() else None)

    step("生成语料")
    cmd = [sys.executable, "tools/convert.py"]
    if live:
        cmd += ["--live", str(live.relative_to(ROOT))]
    run(cmd)

    step("规范链接（去掉指向原站的绝对地址）")
    run([sys.executable, "tools/normalize_links.py"])

    if not args.skip_assets:
        step("补下新增附件")
        run([sys.executable, "tools/fetch_assets.py"])

    if not args.skip_build:
        step("构建静态站")
        run([str(HUGO), "--logLevel", "warn"])
        public = ROOT / "public"
        pages = sum(1 for _ in public.rglob("*.html"))
        print(f"  产物 {pages} 个页面，位于 {public}")

    if args.deploy:
        step("提交并推送")
        run(["git", "add", "-A"])
        run(["git", "commit", "-m", "sync: 从原站同步最新文章与评论"])
        run(["git", "push"])


if __name__ == "__main__":
    main()
