# shared/video-restoration

本地视频高清修复工具（RealBasicVSR x4，空间分块，逐块写帧）。完整规则见 `VSR_WORKFLOW.md`，交接要求见 `CODEX_GROK_HANDOFF.md`。

| 文件 | 用途 |
|---|---|
| `run_vsr_streaming.py` | 单镜推理：CLI 配置、静态校验、GPU 锁、manifest/日志、显存策略与一次 OOM 降级、编码（保留音轨）、解码自检，完成后调用 QA |
| `qa_single_vsr.py` | 只读 QA：硬检查、三态 `fail/needs_review/pending_review`、时序/接缝指标、首中尾与接缝裁切联系表（PNG） |
| `VSR_WORKFLOW.md` | 工作流说明、状态规则、最小验收命令矩阵、限制 |
| `backup/` | 修改前脚本备份（带时间戳） |
| `run_vsr_test01*.py/.ps1`、`run_vsr_streaming*.ps1`、`*.log` | 2026-10-07 早期 c04 尝试的历史脚本与日志（保留，不再使用） |

## 快速开始

```powershell
$py = "E:\program\1project\video\shared\runtime\comfy\installs\portable\python_embeded\python.exe"
$vr = "E:\program\1project\video\shared\video-restoration"
& $py "$vr\run_vsr_streaming.py" --help
& $py "$vr\run_vsr_streaming.py" --input <源.mp4> --baseline <Lanczos.mp4> --output-dir <新run目录> --shot-id <镜头ID> --dry-run
# 2–3 帧 GPU smoke：加 --max-frames 3，换新目录
# 正式：去掉 --dry-run；长任务用 Start-Process 后台跑，轮询 <run目录>\run.log 与 manifest.json
& $py "$vr\qa_single_vsr.py" --run-dir <run目录> --compare-vsr <旧VSR交付版>   # 单独重跑 QA（只读，新文件加时间戳）
```

## 每个 run 目录的产物

`manifest.json`（配置/环境/进度/状态/锁释放/QA 状态）、`run.log`、`<shot>-realbasicvsr-raw-<W*4>x<H*4>.mp4`、`<shot>-realbasicvsr-1920x1080.mp4`、`quality-qa.json`、`contact-first-mid-last.png`、`contact-seam-crops.png`。

## 状态

- `status`：`running` / `completed` / `failed`（失败目录保留，不支持 resume）。
- `qa_status`：`fail`（硬检查失败，推荐回退 Lanczos）/ `needs_review`（自动预警）/ `pending_review`（无预警，待人工）。
- `visual_qa`：自动永远 `pending_review`；人工看联系表并完整播放后才可改 `passed`。

## 批量规则

按 `vsr-input-manifest.json` 顺序串行；每镜独立 run 目录、manifest、日志、QA；任一镜失败即暂停批次，不自动循环重试；不经 GPU 队列时必须遵守 GPU 锁。
