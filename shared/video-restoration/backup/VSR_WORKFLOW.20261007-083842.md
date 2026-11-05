# RealBasicVSR 视频高清修复工作流

入口脚本：`run_vsr_streaming.py`

## 默认行为

- 使用 RealBasicVSR 进行时序超分，按时间块逐批写帧。
- 每个时间块再拆成带重叠边缘的空间 tile，并用加权窗口拼接，降低显存峰值和 tile 接缝。
- 自动按显存选择 tile：`<=10 GB: 176x320`，`10-18 GB: 352x640`，`>18 GB: 512x768`。
- `VSR_TILE_H`、`VSR_TILE_W`、`VSR_TILE_OVERLAP`、`VSR_CHUNK_SIZE` 可显式覆盖自动值。
- 输出 raw 修复视频和 1920x1080 H.264 交付版；交付版从源视频复用音频并重新编码 AAC。
- 源视频、Lanczos 基线和修复版使用独立路径，禁止覆盖。

## QA

运行 `qa_single_vsr.py`，检查：

- 视频帧数、音频流、时长和完整解码；
- 逐帧 Laplacian 边缘能量，作为清晰度变化参考；
- 缩小帧的时序差异，作为闪烁异常预警；
- `quality-qa.json` 中的 `qa_status` 和 `checks`。

数值指标不能替代实际播放检查。出现结构变形、明显闪烁、tile 接缝或假细节时，回退到 Lanczos 或 affine 版本。

## 失败处理

先保留失败目录和日志，不覆盖既有产物。降低 tile 尺寸后重跑；若仍无法稳定产出或修复结果不合格，直接采用 Lanczos 1080p 基线。
