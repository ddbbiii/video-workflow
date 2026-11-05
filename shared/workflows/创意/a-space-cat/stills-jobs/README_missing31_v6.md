# 太空猫 v6：缺镜 31 张首帧准备

更新时间：2026-10-02（北京时间）

## 先说结论

- 已有的 20 张首帧不动：它们不是 `comfy-stills` 出的，而是第 6 步 `refs/shots/shotNN.png` 的外部生图参考，后续用 CPU `scripts/upscale_frame.py`（`realesrgan-anime`，另有 shot30 左裁修正版）放大到 `firstframes/shotNN.png`。证据：`firstframes/README.md`、`approvals/2026-10-01-太空猫_分镜参考图.md`、`refs/prompts.md`。
- 本批 31 镜改走 box 的 `scripts/stills.py jobs` → ddbbi `comfy-stills` runner：20 镜用 `qwen_edit_ref_lightning`（image 1 是 silver-cat-01 ref），11 个空镜用 `qwen_t2i_lightning`。每镜 2 个候选，共 **62 jobs**；runner 会按 workflow 分组。
- 没有启动 ComfyUI、生图或 TTS；这里只生成了任务 JSON 和准备文件。

## 文件

- `missing31_v6.json`：可直接给 runner 的 62-job spec。
- `missing31_v6_shotlist.json`：完整 51 镜副本；只给缺的 31 镜加了 `still` 定义，保留原镜号，供回收后的 gate/pick 使用。
- `E:\program\1project\video\assets\创意\characters\silver-cat-space\laoda_refs\旧参考图_短毛写实.png`（原 `stills-jobs\refs\silver-cat-01_ref.png`，与此文件 md5 相同，2026-10-08 合并）：从 box `projects/a-smoke-cat/characters/silver-cat-01/ref.png` 准备的角色 ref；本机 `chuangyi` 下没有找到同名 `ref.png`，因此不使用研究员三视图或 `A_turnaround` 代替。

## 依赖核对

已在 ddbbi 核到：

- `E:\program\1project\video\shared\runtime\engines\stills-runtime\models\diffusion_models\qwen_image_edit_2511_fp8mixed.safetensors`
- `E:\program\1project\video\shared\runtime\engines\stills-runtime\models\diffusion_models\qwen_image_2512_fp8_e4m3fn.safetensors`
- `E:\program\1project\video\shared\runtime\engines\stills-runtime\models\loras\Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors`
- `E:\program\1project\video\shared\runtime\engines\stills-runtime\models\loras\Qwen-Image-2512-Lightning-4steps-V1.0-bf16.safetensors`
- `E:\program\1project\video\shared\runtime\engines\stills-runtime\models\vae\qwen_image_vae.safetensors`
- 文本编码器在共享目录：`E:\program\1project\video\shared\runtime\comfy\models\models\text_encoders\qwen_2.5_vl_7b_fp8_scaled.safetensors`，由 `extra_model_paths.yaml` 映射。

场景参考图没有作为额外输入：现有 A 线 `stills.py` 流程以角色 ref 做单图 edit，场景/光照写入 prompt；空镜走 t2i。这样不改已有 refs/shots，也不引入超过既有工作流支持范围的参考图。

## 开跑前：GPU 锁

不要现在跑；助眠 TTS 仍在占 GPU。开跑前确认 TTS 已退出，并检查：

```powershell
if (Test-Path 'E:\program\1project\video\shared\work\cache\gpu.lock') { Get-Content -Raw 'E:\program\1project\video\shared\work\cache\gpu.lock' }
Get-CimInstance Win32_Process -Filter "Name like 'python%'" | ? { $_.CommandLine -match 'shared\runtime\engines\tts|voxcpm|index-tts|gen_shots|indextts' } | select ProcessId,CommandLine
```

不需要手写锁。`run_stills.py` 会先等活的 `gpu.lock`、TTS Python、以及其他 CUDA Python 进程全部消失，再写入 `E:\program\1project\video\shared\work\cache\gpu.lock`；结束（含异常）会关闭它自己启动的 ComfyUI 并释放锁。**不要删除别人的活锁，也不要在 TTS 运行时强行开跑。**

## 直接开跑（一句话）

TTS 放锁、上面的检查确认没有占用后，在 ddbbi PowerShell 执行：

```powershell
powershell -ExecutionPolicy Bypass -File E:\program\1project\video\shared\runtime\engines\stills-runtime\scripts\run_stills.ps1 -Jobs E:\program\1project\video\shared\workflows\创意\a-space-cat\stills-jobs\missing31_v6.json
```

这是后台启动 runner，不是 ComfyUI 前台/浏览器启动。完成标志：
`E:\program\1project\video\shared\runtime\engines\stills-runtime\logs\stills_a-space-cat_missing31_v6.log` 最后一行出现 `=== END ok=... fail=...`。

## 跑完回收和验收（box）

runner 会在 `E:\program\1project\video\shared\exchange\pipeline\stills\a-space-cat_missing31_v6.zip` 写结果。把该 zip CopyToBox 后，在 `/workspace/kepu-pipeline` 执行：

```bash
.venv/bin/python scripts/stills.py unpack --zip <zip> --raw-dir projects/a-space-cat/stills-raw
.venv/bin/python scripts/stills.py gate --shotlist projects/a-space-cat/stills-jobs/missing31_v6_shotlist.json --profile profiles/a-animal.yaml --raw-dir projects/a-space-cat/stills-raw --jobs projects/a-space-cat/stills-jobs/missing31_v6.json --pick --stills-dir projects/a-space-cat/firstframes/missing31_v6
```

第二条只在 box 上 CPU 跑 gate，并把通过/最佳候选写到隔离目录 `firstframes/missing31_v6/shot_XX_sXX.png`；不会覆盖已有 20 镜。审核通过后再把缺镜候选按项目现有命名规则整理成 `firstframes/shotNN.png`。当前本批任务本身不会改 `firstframes`。
