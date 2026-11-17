# -*- coding: utf-8 -*-
"""抖音参考片获取：本机 douyin-media-mcp 的薄封装。

MCP 本体通常与 video 仓库并列放置于 `../douyin-media-mcp/`（stdio MCP，三种工具）；
也可通过 `DOUYIN_MCP_ROOT` 指定位置。
本脚本不做协议握手，直接调它的 service 层，供工作区命令行使用。

用法（工作区根目录）：
  python shared/tools/douyin-ref/fetch_ref.py "<分享链接>" [--out work/refs/20261110] [--quality 720p]

注意：
- 浏览器解析依赖 Playwright 起 Chromium；DSH 的 workspace-write 沙箱会禁止管道创建，
  必须用 danger-full-access 跑本脚本（一次性审批），否则报 PermissionError [WinError 5]。
- 只处理用户有权保存的内容；不绕过登录、验证码、付费墙；不提供去水印。
- 输出目录里会写 `<视频>.manifest.json`，不含 Cookie 与签名 URL。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[3]
MCP_ROOT = Path(os.environ.get("DOUYIN_MCP_ROOT", "../douyin-media-mcp")).expanduser()
if not MCP_ROOT.is_absolute():
    MCP_ROOT = WORKSPACE / MCP_ROOT
MCP_ROOT = MCP_ROOT.resolve()


def clean_env() -> None:
    # 本机 NO_PROXY 含 "[::1]"，httpx 会当 URL 解析；抖音是国内站点，直连。
    for key in list(os.environ):
        if key.lower() in {"all_proxy", "http_proxy", "https_proxy", "no_proxy"}:
            del os.environ[key]
    # 不能往外部仓库写 __pycache__（沙箱/权限）
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"


async def run(url: str, out_dir: Path, quality: str, name: str | None, overwrite: bool) -> dict:
    sys.path.insert(0, str(MCP_ROOT / "src"))
    from douyin_media_mcp.service import DouyinMediaService

    service = DouyinMediaService()
    out_dir.mkdir(parents=True, exist_ok=True)
    return await service.download(
        url,
        str(out_dir),
        quality=quality,  # type: ignore[arg-type]
        filename=name,
        overwrite=overwrite,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="用本机 douyin-media-mcp 下载参考视频")
    parser.add_argument("url", help="抖音分享链接（v.douyin.com/... 或 www.douyin.com/video/...）")
    parser.add_argument(
        "--out",
        default=str(WORKSPACE / "work" / "refs" / datetime.now().strftime("%Y%m%d")),
        help="输出目录，默认 work/refs/<今天>",
    )
    parser.add_argument("--quality", default="best", choices=["best", "1080p", "720p"])
    parser.add_argument("--name", default=None, help="输出文件名（默认 douyin-<aweme_id>.mp4）")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    clean_env()
    out_dir = Path(args.out)
    try:
        result = asyncio.run(run(args.url, out_dir, args.quality, args.name, args.overwrite))
    except Exception as exc:  # noqa: BLE001
        payload = getattr(exc, "payload", None)
        print(json.dumps(payload() if callable(payload) else {"status": "error", "error": repr(exc)},
                         ensure_ascii=False, indent=2))
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
