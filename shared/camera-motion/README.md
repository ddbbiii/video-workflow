# 通用静帧运镜

各助手执行推拉平移前请读取 [共享运镜规则](MOTION_GUIDELINES.md)。具体幅度、时长和缓冲参数需逐镜调整，但不得低于其中的默认下限；渲染前先跑 `validate_plan.py`。

适用于任何主题。引擎不内置助眠、悬疑或科普节奏，不修改图片、配音或字幕。支持已验证的浮点仿射后端，以及可选的 Blender 正交相机后端。默认仍是 `affine`；缺少 Blender 时请求 `backend:blender` 会明确报错，不会静默回退。

## 使用

依赖 Python、NumPy、Pillow、OpenCV，系统 PATH 提供 FFmpeg/ffprobe。Blender 后端另需 Blender 4.5 LTS（已在 4.5.14 便携版验证）。

```sh
python shared/camera-motion/validate_plan.py path/to/plan.json
python shared/camera-motion/camera_motion.py path/to/plan.json --out path/to/new-run --validate-only
python shared/camera-motion/camera_motion.py path/to/plan.json --out path/to/new-run
python shared/camera-motion/camera_motion.py path/to/plan.json --out path/to/new-run --resume
python shared/camera-motion/camera_motion.py path/to/plan.json --out path/to/new-run --blender blender
python -m unittest discover -s shared/camera-motion -p 'test_*.py'
python shared/camera-motion/verify_motion.py path/to/new-run
```

从仓库根目录运行以上命令。Blender 可执行文件可以加入 `PATH`；否则通过 `--blender` 传入本机位置，或在 shell 中设置 `CAMERA_MOTION_BLENDER`。

每个镜头包含：唯一 `id`、相对配置文件的 `source`、`duration_s`、`start_view`/`end_view`，可选 `curve` 和 `required_regions`。取景框是原图归一化 `[x,y,width,height]`，必须位于图片内部并匹配输出画幅。不同画幅需显式指定裁切框，不拉伸、不自动猜裁切。关键主体区域必须同时包含在起止框内。

全局配置：`schema_version:1`、`backend`（`affine` 或 `blender`）、`output:{width,height,fps}`、`shots`，可选 `overview` 和 `transition_s`。Blender 可选字段：

- `blender_exe`：可执行文件路径（也可用环境变量 `CAMERA_MOTION_BLENDER` 或 CLI `--blender`）
- `blender_engine`：默认 `CYCLES`（CPU）。`BLENDER_EEVEE_NEXT` / `BLENDER_EEVEE` 会走 GPU，需占有 `shared/work/cache/gpu.lock`；检测到 `shared/runtime/comfy/cache/gpu.lock` 时也必须视为已有占用，不得覆盖或删除。
- `blender_use_gpu`：Cycles 是否用 GPU（默认 false）
- `blender_samples`：Cycles 固定采样数，默认 4；关闭自适应采样和逐帧随机种子
- `blender_interpolation`：纹理取样，默认 `Linear`；可选 `Closest` / `Cubic`，需自行验证细纹理运动

帧率为整数；时长和转场按完整帧对齐。镜头时长可以不同。输出包含 MP4、每帧取样矩阵、源文件/参数/引擎指纹及运行清单。Blender 还会在 `frame_cache/<shot_id>/<cache_key>/frames/` 写可恢复的无损 PNG 序列。缓存键包含源图、轨迹、渲染参数、脚本和 Blender 可执行文件身份；恢复前验证 PNG 完整性与尺寸。恢复时校验输出哈希，参数不同必须使用新目录。编码失败不会把 partial 文件当完成资产。

速度曲线支持 `linear`、`smoothstep` 和 `ramped_linear`（附 `ramp_s`）。最后一帧精确落在终点；实际运动时段为 `(帧数-1)/fps`。短镜与长镜均按实际时段计算，视频时长仍为 `帧数/fps`。仿射与 Blender **共用** `progress` / `view_at`，不另起一套速度定义。

`*-trajectory.json` 声明坐标系，并提供 `inverse_sample_matrices`；相邻帧变换为 `inv(P_next) @ P_current`。

## Blender 后端要点

- 无界面：`blender --background --factory-startup --python blender_scene.py -- --job job.json`（`--factory-startup` 避免加载用户偏好/插件，例如会占 8765 端口的 AI MCP）
- 正交相机 + 原图像素单位平面；Emission 材质，无光照/无运动模糊；色彩管理 Standard（非 AgX）
- `ortho_scale`：AUTO sensor fit 下取可见区较大边；需用棋盘格实测起止与方向
- UV 默认不翻转 V，源图左上对应画面左上
- 默认 Cycles CPU，避免与生图流水线抢 GPU
- 请求的引擎不可用时直接失败，不自动切换引擎或设备
- `compare_backends.py` 的 `matched_frame_pixel_difference` 包含采样、几何与压缩差异，不是独立的色彩漂移测量

## 验收矩阵素材

`testdata/` 含棋盘、小字、星点、岩层与照片，以及 6 组 affine/blender 成对配置（横竖屏、同画幅/跨画幅、材料对照）。见 `testdata/MANIFEST.json`。

## 吸收的开源设计

- [MLT affine](https://www.mltframework.org/plugins/FilterAffine/)：显式几何参数；本引擎用归一化取景框，未复制源码。
- [Blender 相机](https://docs.blender.org/manual/en/latest/render/cameras.html) / [Python API](https://docs.blender.org/api/current/)：正交相机与确定性逐帧求值；须与相同轨迹的仿射输出比较后再谈默认后端。
- [OpenCV warpAffine](https://docs.opencv.org/4.x/da/d54/group__imgproc__transform.html)：浮点变换及 bicubic 取样。
- Pillow Lanczos 预滤波、FFmpeg/libx264 编码。

仅借鉴公开设计并调用库 API，不将 Blender/MLT 的源代码复制进本工具。

## 验收边界

引擎验证参数、边界、主体区域、输出帧数/尺寸/帧率和完整解码，报告规划轨迹变化量。它不会将这些检查当成“实际画面无抖动”的证明。实际视频仍需测连续帧运动相对目标曲线的误差，并检查硬边和纹理闪烁、播放观感。若 Blender 质量收益很小但成本显著更高，应保留 affine 为默认。

没有自动深度/分层视差、内部动画、超分、插帧、音乐。新增这些能力需明确素材与规则。
