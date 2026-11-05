# 创意 workflow 脚本

这里放的是已完成的太空猫（`a-space-cat`）这一集的生产脚本和任务配置。2026-10-08 由视频号规划从 `projects\创意\legacy-source\chuangyi\` 移过来，原 legacy 目录已经删除。

- `a-space-cat\`：沿用原来的子目录结构，包括 `audio\`（TTS 任务）、`i2v\`、`out\`（missing31 挑图和放大）、`stills-jobs\`（生图任务），以及 `finalize_a_space_cat_v6.py`。
- `lora-training\`：银渐层猫 LoRA v4 的训练脚本，原来在 `legacy-xfer\`。

脚本里的绝对路径已经按新布局改写，但**改完没有重跑过**。改写依据是 `projects\创意\logs\legacy-migration-manifest.csv`：
- 素材、日志、质检报告指向 `projects\创意\episodes\a-space-cat\` 下对应的位置。
- 脚本之间的互相引用指向本目录。
- `comfy-stills` 改成 `shared\runtime\engines\stills-runtime`。
- GPU 锁改成 `shared\work\cache\gpu.lock`。
- 桌面中转目录改成 `shared\exchange\pipeline\stills`。

i2v 和 finalize 脚本里基于 `BASE` 拼出来的相对路径也一起改了：clips 指向 `video\clips\`，首帧指向 `image\firstframes\`，分镜指向 `storyboard\`，状态文件指向 `logs\`，i2v 工作目录指向 `archive\i2v_raw\`。

## 已知没解决的引用

1. 三个 `i2v\run_a_space_cat_i2v_*.py` 用 `sys.path.insert(0, r'C:\Users\10060\AppData\Local\Temp')` 导入 `i2v_cmp`，GPU 锁路径 `m.LOCK` 也来自这个模块。但 Temp 里的 `i2v_cmp.py` 已经不在了（C 盘清理时删掉的），所以这三个脚本照原样跑不起来。别处还有副本，例如 `shared\work\scratch\legacy-root\i2v-cmp-2026-10-01\i2v_cmp.py` 和 `shared\workflows\猎奇\tudou\i2v\i2v_cmp.py`。要重跑的话，得先确认用哪一版，再改 sys.path。
2. 三个 `out\missing31_upscale*.py` 用的放大模型在 `C:\Users\10060\agent-tools\shot30\RealESRGAN_x4plus_anime_6B.pth`。文件还在，路径没改。
3. 有几处 box 路径没改：`firstframes\run_upscale.sh` 里的 `/workspace/kepu-pipeline`、生图任务 json 里的 `/workspace/kepu-pipeline/projects/a-smoke-cat/characters/silver-cat-01/ref.png`，以及 `stills-jobs\README_missing31_v6.md` 里的 box 命令。
4. `shared\exchange\pipeline\stills\` 目前不存在。生图任务的 `pull_zip` 都指向这里，跑之前要先建好这个目录，或者改 runner。
5. `stills-jobs\plot_local_v1.json` 的 `pull_zip` 原本就写成了 `a-space-cat_missing31_v6.zip`，看起来是复制时留下的错，没动。
6. 有几处输出路径现在还不存在，跑的时候会自动生成：`image\stills-raw\plot_event_v1\`（plot_event_v1 还没出图）、`logs\i2v\ltx_draft.exit`。
7. 原来的 `stills-jobs\refs\silver-cat-01_ref.png` 和 `assets\创意\characters\silver-cat-space\laoda_refs\旧参考图_短毛写实.png` 是同一个文件（md5 相同），已经删掉，只保留 assets 那份。runner 实际读取的是 `shared\runtime\engines\stills-runtime\refs\...\silver-cat-01_ref.png`，这个文件还在。
8. `lora-training\train-a-pet-silverlonghair-v4.ps1` 的 HF 缓存仍然是 `shared\runtime\comfy\cache\hf`。目录存在，没改。
9. `README_missing31_v6.md` 里的相对路径，例如 `firstframes/README.md`、`refs/shots/`、`scripts/upscale_frame.py`，都是当时的记录，没有改。
