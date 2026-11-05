# RealBasicVSR 单镜高清修复工作流（v2，2026-10-07）

入口：`run_vsr_streaming.py`（推理 + 编码 + 解码自检，结束后自动调用 QA）、`qa_single_vsr.py`（独立、只读 QA）。
Python：`E:\program\1project\video\shared\runtime\comfy\installs\portable\python_embeded\python.exe`（torch 2.11+cu128、modelscope 1.40.1、opencv 5.0）。
旧版脚本备份：`backup\run_vsr_streaming.20261007-083842.py`、`backup\qa_single_vsr.20261007-083842.py`、`backup\VSR_WORKFLOW.20261007-083842.md`。

## 不变的部分（已验收画面风格）

- 模型 `damo/cv_realbasicvsr_video-super-resolution_videolq`，x4；空间 tile 加权窗口拼接（重叠区线性斜坡）；时间块默认 1 帧。
- raw 为 x4 mp4v 中间件；交付版 `scale=W:H:flags=lanczos,setsar=1`、libx264 `-preset slow -crf 14`、yuv420p、`+faststart`。
- 注意：1280x704 源直接缩放到 1920x1080，与旧版一致（宽高比 1.818→1.778，约 2.3% 纵向拉伸），未改。

## 正式调用

```powershell
$py = "E:\program\1project\video\shared\runtime\comfy\installs\portable\python_embeded\python.exe"
$vr = "E:\program\1project\video\shared\video-restoration"
$R  = "E:\program\1project\video\projects\助眠解说\legacy-source\zhumian\b-geomagnetic-reversal\gen_rebuild\runs"
# 1) 先 dry-run（不加载模型、不占 GPU、不建目录）
& $py "$vr\run_vsr_streaming.py" --input "$R\20261007-ltx-cinematic-retry-c04\ch1-c04-v2-01-raw-1280x704.mp4" `
  --baseline "$R\20261007-ltx-cinematic-retry-c04\ch1-c04-v2-01-1920x1080-hq.mp4" `
  --output-dir "$R\20261007-vsr-rerun-<批次>\<镜头>-<runid>" --shot-id ch1-c04-v2-01 --dry-run
# 2) 去掉 --dry-run 正式运行（建议 Start-Process 后台跑并轮询 run.log / manifest.json）
#    可选 --qa-compare <旧VSR交付版> 让 QA 联系表多一列对比
```

主要参数（`--help` 显示全部和默认值）：`--input` `--baseline` `--output-dir`（必须不存在、父目录必须存在）`--output-size 1920x1080` `--model` `--tile-size auto|WxH`（输入像素，8 的倍数，>=64）`--overlap 32` `--chunk-size 1` `--max-frames 0`（smoke 用）`--drop-audio` `--dry-run` `--shot-id` `--device auto|cuda|cpu` `--reserve-gb 2` `--no-qa` `--qa-compare` `--lock-path` `--lock-owner zhumian-vsr-rerun`；`--inject-failure` 仅测试用。

退出码：0 完成且 QA 非 fail；1 运行失败（manifest `status=failed`）；2 配置/参数/输入被拒；3 输出目录已存在；4 GPU 锁被占；5 运行完成但 QA=fail。

## 安全门与记录

- 加载模型前完成静态校验：输入缺失/非视频/不可解码、输出目录已存在、tile/overlap/chunk/输出尺寸非法、ffmpeg/ffprobe 缺失 → 非零退出，不建目录、不占锁。
- GPU 锁：`shared\work\cache\gpu.lock` 独占创建（owner/pid/token/run_dir/started）；`shared\runtime\comfy\cache\gpu.lock` 若存在则作为旧锁保护拒绝启动。只删除 pid+token 属于本进程的锁；进程被硬杀会留下锁，需人工确认 pid 已不存在后再处理，脚本绝不删除他人锁。锁释放结果写入 manifest `lock_release`。
- 正式运行：先占锁 → 独占创建 run 目录 → 立即写 `manifest.json`（配置、输入大小/mtime、ffprobe、模型、Python/Torch/CUDA/FFmpeg/OpenCV/NumPy/ModelScope 版本、nvidia-smi GPU 名称与显存）。所有 manifest 更新为临时文件 + 原子替换。
- 阶段：`preflight_decode → model_load → select_tiles → inference → encode → verify_decode → done`。任何异常（含 Ctrl-C）写 `status=failed`、`failed_stage`、`error_type`、`error_summary`、`traceback_tail`、`frames_completed`，退出码 1，目录保留。
- 每个时间块后更新 `frames_completed`/`progress`/`last_chunk`（帧范围、耗时、显存），并写 `run.log`。

## 显存策略

- `--tile-size auto`：CUDA 上读当前空闲显存，`空闲 - reserve(2GB) >= 6GB` 用已验证 640x352，否则 320x176，<1GB 直接失败；CPU 用 320x176。选择依据写入 `tile_selection`。
- CUDA OOM：清缓存，tile 长宽减半，重试当前时间块一次；之后再 OOM 即停机写 failed。降级记录 `oom_downgrade`，`tile_history` 记录各段 tile 布局，`tiles_final` 为最终参数。

## 音轨

- 输入有音轨：映射 `1:a:0`，AAC 192k，保留；不再用 `-shortest`（时长由 QA 硬检查）。`--max-frames` 部分运行时用 `-t` 把音频裁到已处理时长。
- 输入无音轨：输出无音轨。只有显式 `--drop-audio` 才丢弃已有音轨。

## QA（`qa_single_vsr.py`，只读）

调用：`python qa_single_vsr.py --run-dir <run目录> [--compare-vsr <旧VSR>]`；或对现有资产只读：`--input --vsr [--raw] [--baseline] --report-dir <新目录> [--tile-size 640x352 --overlap 32]`。

- 硬检查（任一失败 → `qa_status=fail`）：视频流=1、分辨率=目标、帧率=输入、h264、yuv420p、帧数=期望（ffprobe 与逐帧解码）、容器/视频时长差<0.1s、音轨规则（保留时存在且音视频时长差<0.1s；无音轨/丢弃时不存在）、交付版与 raw 完整解码、raw 为输入 x4。
- 自动预警（→ `needs_review`）：P95 缩小帧时序差 > max(8, 基线×2.5)；相邻帧平均亮度跳变 > max(3, 基线×2.5)；Laplacian 逐帧变异系数 > max(0.10, 基线×2.5)；tile 接缝。
- 接缝指标：各 tile 边界（按 `tile_history` 映射到交付像素）±2px 带的平均梯度 / 非边界线中位梯度，并与 Lanczos 基线同位置比较；`vsr_score>1.25` 且 `相对值>1.25` 记为疑似。
- 无硬失败无预警也只到 `pending_review`。`visual_qa` 永远由 QA 写为 `pending_review`；只有人工看过联系表并完整播放后，才可人工改为 `passed`。
- 产物：`quality-qa.json`、`contact-first-mid-last.png`（输入现场 Lanczos / 基线 / 新 VSR / 可选旧 VSR × 首中尾）、`contact-seam-crops.png`（边界交点 1:1 裁切，2x 最近邻放大）；再次运行不覆盖，加时间戳后缀。
- Laplacian 方差只是边缘能量，不能证明真实细节恢复；时序/接缝指标只是预警。
- QA 不通过：保留 VSR 文件诊断，`recommended_delivery` 指向 Lanczos 基线；无基线则只报告失败。

## 最小验收命令矩阵（2026-10-07 实测，目录 `runs\20261007-vsr-rerun-geomag-b01\tests\`）

| 场景 | 命令要点 | 预期 | 实测 |
|---|---|---|---|
| 帮助 | `--help` | 0，列出全部参数和默认值 | 0 |
| dry-run | 有效 c04 输入 `--dry-run` | 0，打印规范化配置；不加载模型、不建目录 | 0；目录未创建 |
| 输入缺失 | `--input 不存在.mp4` | 非零，说明阶段 | 2，`validate_input` |
| 非视频 | `--input not-a-video.mp4` | 非零 | 2，`probe_input` |
| 输出目录已存在 | `--output-dir existing-dir` | 非零，内容与时间戳不变 | 3，前后一致 |
| 非法 tile/overlap/chunk | `--tile-size 100x50` / `--overlap 200` / `--chunk-size 0` | 加载模型前非零 | 2/2/2，`validate_args` |
| 模型加载失败 | `--inject-failure model_load` | 非零，failed manifest + log | 1，`failed_stage=model_load`，锁已释放 |
| 编码失败 | `--device cpu --max-frames 1 --inject-failure encode` | 非零，failed manifest + log | 1，`failed_stage=encode`，`frames_completed=1` |
| OOM 一次降级 | `--device cpu --max-frames 2 --tile-size 640x352 --inject-failure oom_once` | 降到 320x176 后完成 | 0，`oom_downgrade` 已记录，QA `pending_review` |
| OOM 两次 | `... --inject-failure oom_twice` | 停机，failed | 1，`failed_stage=inference` |
| GPU smoke 2–3 帧 | `--max-frames 3`（新目录） | 输出、manifest、QA、联系表；帧数/分辨率/音轨正确；锁释放 | 见 README / 本批次报告 |

## 限制

- 不支持断点续跑：失败后保留目录，换新 `--output-dir`（新 run-id）全量重跑；不从未闭合 MP4 猜测进度。
- 人工视觉检查（联系表 + 完整播放）无法自动化；自动 QA 永不给最终通过。
- raw 中间件为 mp4v 有损编码（沿用旧路径）。
- 接缝/时序指标为全线平均，局部短时闪烁或局部接缝可能漏检。
