# 抖音参考片获取（douyin-media-mcp）

> 生效：2026-11-10。触发：用户给出抖音分享链接、或做线路评估/拆解需要看参考片时，**先读本文件**。
> 本文件是"怎么把抖音参考片落到本地"的唯一入口；线路 planning 里只引用，不复制命令。

## 0 一句话

工具仓库 `douyin-media-mcp` 默认与本仓库并列，路径为 `../douyin-media-mcp/`；也可通过 `DOUYIN_MCP_ROOT` 指定其他位置。工作区封装为 `shared/tools/douyin-ref/fetch_ref.py`。一条命令下载视频与 manifest；浏览器解析必须用完全访问权限跑（见 §3）。

## 1 三件东西

| 件 | 位置 | 作用 |
|---|---|---|
| MCP 服务 | `../douyin-media-mcp/`（相对于本仓库根目录） | stdio MCP，暴露 3 个工具；版本 `0.1.0.dev0`，MIT |
| 运行环境 | MCP 仓库内的虚拟环境 | Windows: `.venv/Scripts/python.exe`；macOS/Linux: `.venv/bin/python` |
| 工作区封装 | `shared/tools/douyin-ref/fetch_ref.py` | 直接调 service 层，命令行用；不依赖 MCP 握手 |

MCP 工具：`resolve_douyin_url`（只解析）、`download_douyin_media`（下载+封装+验收）、`probe_media`（本地媒体验收）。
接口契约与错误码见 `<MCP>\docs\MCP_CONTRACT.md`；已验证链路见 `<MCP>\docs\VERIFIED_PIPELINE.md`。

**Codex / Claude 注册**（DSH 不需要，DSH 用 §2 的封装脚本）：

```toml
[mcp_servers.douyin-media]
command = "uv"
args = ["--directory", "<douyin-media-mcp repository path>", "run", "douyin-media-mcp"]
startup_timeout_sec = 30
tool_timeout_sec = 1800
```

## 2 标准流程

```sh
python shared/tools/douyin-ref/fetch_ref.py \
  "https://v.douyin.com/XXXXXX/" \
  --out work/refs/20261110 \
  --overwrite
```

从仓库根目录运行。如果 `douyin-media-mcp` 不在并列目录中，先设置 `DOUYIN_MCP_ROOT` 指向其位置，再运行封装脚本。

1. 链接可以是 `v.douyin.com/...` 短链，也可以是 `www.douyin.com/video/<aweme_id>`。
2. `--quality`：`best`（默认）/ `1080p` / `720p`；**这是偏好不是保证**，以返回值 `width/height` 为准。
3. 返回 `status: "completed"` 才算成功；`media_mode` 按最终文件实际音视频流判断。页面没有独立音频候选不代表作品无声：音频可能已封装在视频流中，MCP 会保留它。
4. 需要单独分析音频时设置 `keep_separate_streams: true`；返回的 `.audio.m4a` 与 `.video.mp4` 分别是独立音轨和纯视频轨。
5. 输出目录（默认 `work/refs/<YYYYMMDD>/`）里会多一个 `<视频>.manifest.json`：时长、分辨率、码率、sha256、候选选择理由，**不含 Cookie 与签名 URL**。
6. 抽帧验收：`ffmpeg -i <视频> -vf "fps=1/20,scale=480:-1,tile=4x5" -frames:v 1 sheet.jpg`，先看结构再逐段拆。
7. 拆解结论写进对应线路的 `planning/参考拆解-<日期>.md`，并把本文件路径放在"取证"一节。

## 3 权限与沙箱（必须知道）

- **workspace-write 模式下一定失败**：Playwright 要起 Chromium 子进程，沙箱禁止管道创建，报 `PermissionError [WinError 5]` 或 `[sandbox: file access denied]`。
- 正确做法：该命令用**完全访问**（`danger-full-access`/完全权限）执行。2026-11-10 已实测：完全访问下两条链接均成功（见 §7）。
- 报错先看是不是权限/管道，**不要据此判断"没有工具"或"拿不到参考片"**。
- 不要在外部仓库写 `__pycache__`：封装脚本已设 `PYTHONDONTWRITEBYTECODE=1`，手工调用时也要设。
- 本机 `NO_PROXY` 含 `[::1]`，httpx 会把它当 URL 解析报错；封装脚本会清掉代理变量，手工调用需同样处理（见 `fetch_ref.py` 的 `clean_env()`）。

## 4 合规边界（硬）

- 只处理用户有权访问和保存的内容；不绕过登录、验证码、DRM、付费墙；不提供去水印。
- 下载物只作**内部参考拆解**，不二次分发、不进成品、不切片当素材用。
- 拆解只写"可借鉴的形式"（节奏、结构、片头骨架），**不抄文案、画面、音轨、BGM、现成梗**。
- 下载物不进 git；manifest 里已有敏感字段清洗，不要手工把 Cookie/签名 URL 写回文档。

## 5 故障排查

| 症状 | 原因 | 处理 |
|---|---|---|
| `PermissionError [WinError 5]`、`CreateFile`、管道相关 | 沙箱禁止子进程管道 | 用完全访问重跑本命令 |
| `AUTH_REQUIRED` / `HUMAN_ACTION_REQUIRED` | 需登录或验证码 | 让用户在自己的浏览器打开一次；不自动绕过 |
| `media_mode: video_only` + 警告 | 检查确认最终媒体确实没有音轨 | 画面仍可用；需要声音时可尝试 MCP 的其他授权解析路径，不能把未取得音频描述成已验证的原声 |
| 请求 1080p 得到 720p | 页面当次只给 720p | 以返回值为准，不反复重试 |
| `SIGNED_URL_EXPIRED` | 签名地址过期 | 重跑（签名地址不落盘、不复用） |
| `FFMPEG_NOT_FOUND` | PATH 里没有 ffmpeg | 将 ffmpeg/ffprobe 加入 `PATH`，或通过 `DOUYIN_MCP_FFMPEG` / `DOUYIN_MCP_FFPROBE` 指定可执行文件位置 |
| 解析为空、页面 404 | 作品被删/限流/需要登录 | 换链接或让用户确认；不要用第三方接口硬抓 |

## 6 归档

- 原件：`work/refs/<YYYYMMDD>/`，按日期分目录；不覆盖历史。
- 拆解图：放对应线路 `planning/refs/`，只留拼版和关键帧，不留整段视频。
- 用完原件不自动删除；清理需用户授权。

## 7 最近验证

| 日期 | 链接 | 结果 |
|---|---|---|
| 2026-11-10 | `v.douyin.com/FrACP9ZhLZA`（250斤肥宅逆袭） | 361.9 s、1920×1080、30 fps、AAC、55.3 MB |
| 2026-11-10 | `v.douyin.com/vlmxLCg2Byc`（顶级下头女） | 361.0 s、1280×720、30 fps、AAC、34.5 MB |

## 8 维护

- 改 MCP 代码、升级依赖或换机器后，用 §7 的两条链接做一次回归，更新"最近验证"。
- 本文件与封装脚本同属工具真源；线路规则不复制命令，只引用本文件。
- 规则写回记入 `README.md` 的"最近写回"。
