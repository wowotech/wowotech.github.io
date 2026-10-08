"""从原站下载正文引用的附件到 static/ 下，保持原路径（/content/uploadfile/...）。

对原站友好：并发受限、失败只记一次不重试轰炸、已存在的文件跳过。
"""
from __future__ import annotations

import configparser
import ftplib
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _origin() -> tuple[str, str]:
    """优先走源站别名 + Host 头：直接批量请求 CDN 会被 WAF 判为攻击返回 403。"""
    cfg = configparser.ConfigParser()
    cfg.read(ROOT / "config" / "config.ini", encoding="utf-8")
    if not cfg.has_section("origin"):
        return "http://www.wowotech.net", ""
    base = cfg["origin"].get("fetch_url") or cfg["origin"].get("base_url", "http://www.wowotech.net")
    return base.rstrip("/"), cfg["origin"].get("fetch_host", "")


def _ftp_conf() -> tuple[str, str, str, str]:
    cfg = configparser.ConfigParser()
    cfg.read(ROOT / "config" / "config.ini", encoding="utf-8")
    if not cfg.has_section("ftp"):
        return "", "", "", "/wwwroot"
    return (cfg["ftp"]["host"], cfg["ftp"]["user"], cfg["ftp"]["password"],
            cfg["ftp"].get("root", "/wwwroot").rstrip("/"))


BASE, HOST_HEADER = _origin()
FTP_HOST, FTP_USER, FTP_PASS, FTP_ROOT = _ftp_conf()
UA = {"User-Agent": "Mozilla/5.0 (compatible; wowotech-migration/1.0)",
      "Referer": f"http://{HOST_HEADER or 'www.wowotech.net'}/"}
if HOST_HEADER:
    UA["Host"] = HOST_HEADER
WORKERS = 5

# 语料里出现的本站资源路径（正文图片与论坛插件图片）
ASSET_RE = re.compile(r"(?:/content/uploadfile/|/forum/plugins/)[A-Za-z0-9._/\-%]+", re.I)


def scan_referenced() -> set[str]:
    """从语料反推需要本地化的附件：清单是派生物，不该与内容漂移。"""
    found: set[str] = set()
    for f in (ROOT / "content").rglob("*.md"):
        found.update(ASSET_RE.findall(f.read_text(encoding="utf-8", errors="replace")))
    for f in (ROOT / "data" / "comments").glob("*.json"):
        found.update(ASSET_RE.findall(f.read_text(encoding="utf-8", errors="replace")))
    return found


def download(rel: str) -> tuple[str, str, int]:
    dest = ROOT / "static" / rel.lstrip("/")
    if dest.exists() and dest.stat().st_size > 0:
        return rel, "skip", dest.stat().st_size
    url = BASE + urllib.parse.quote(rel)
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=45) as r:
            data = r.read()
        if r.status != 200 or not data:
            return rel, f"http{r.status}", 0
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return rel, "ok", len(data)
    except urllib.error.HTTPError as e:
        return rel, f"http{e.code}", 0
    except Exception as e:
        return rel, f"err:{type(e).__name__}", 0


def main():
    manifest = ROOT / "recon" / "assets.txt"
    listed = set()
    if manifest.exists():
        listed = {l.strip() for l in manifest.read_text(encoding="utf-8").splitlines() if l.strip()}
        # 历史上出现过两行粘连的坏条目，这里一并剔除
        listed = {p for p in listed if p.count("/content/uploadfile/") <= 1}
    refs = sorted(scan_referenced() | listed)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text("\n".join(refs) + "\n", encoding="utf-8")
    print(f"清单：内容引用 {len(refs)} 个附件")
    if len(sys.argv) > 1 and sys.argv[1] == "--dry":
        print(f"{len(refs)} refs")
        return

    ok = skip = 0
    failed: list[tuple[str, str]] = []
    done = 0
    with ThreadPoolExecutor(WORKERS) as pool:
        for rel, status, size in pool.map(download, refs):
            done += 1
            if status == "ok":
                ok += 1
            elif status == "skip":
                skip += 1
            else:
                failed.append((rel, status))
            if done % 100 == 0:
                print(f"  {done}/{len(refs)} …", flush=True)

    # HTTP 失败的用 FTP 兜底（这些文件在源站上确实存在，只是 CDN 会 403）
    if failed and FTP_HOST:
        print(f"  {len(failed)} 个失败项改用 FTP 兜底…", flush=True)
        try:
            ftp = ftplib.FTP(FTP_HOST, timeout=120)
            ftp.login(FTP_USER, FTP_PASS)
            ftp.set_pasv(True)
            still = []
            for rel, _status in failed:
                dest = ROOT / "static" / rel.lstrip("/")
                try:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    with dest.open("wb") as fh:
                        ftp.retrbinary(f"RETR {FTP_ROOT}{rel}", fh.write)
                    ok += 1
                except Exception as e:  # noqa: BLE001
                    still.append((rel, f"ftp:{type(e).__name__}"))
            failed = still
            ftp.quit()
        except Exception as e:  # noqa: BLE001
            print(f"  FTP 兜底不可用：{e}")

    total = sum(f.stat().st_size for f in (ROOT / "static").rglob("*") if f.is_file())
    lines = [f"下载 {ok}，已存在 {skip}，失败 {len(failed)}，static/ 合计 {total/1e6:.1f} MB", ""]
    lines += [f"{s}\t{r}" for r, s in failed]
    (ROOT / "recon" / "assets_report.txt").write_text("\n".join(lines), encoding="utf-8")
    print(lines[0])


if __name__ == "__main__":
    main()
