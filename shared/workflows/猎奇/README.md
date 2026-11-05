# 猎奇 workflow 脚本

这里是已完成的《土豆退婚流》（`tudou`）这一集的生产脚本和任务配置，2026-10-08 由视频号规划从 `projects\猎奇\legacy-source\lieqi\` 移过来，原 legacy 目录已删。

- `scripts\`：猎奇自己的生图 runner `run_lieqi.ps1`、`run_lieqi.py`，和首轮参考图任务 `tudou-refs-v1.json`
- `tudou\`：成片合成 `finalize_lieqi_v3.py`（v1 是 `finalize_lieqi.py`），流水线 `pipeline_v3.ps1`，任务生成 `make_jobs.py`
- `tudou\i2v\`：i2v 的各个 runner，和它们共用的模块 `i2v_cmp.py`
- `tudou\voice\`、`tudou\firstframes\`：配音和 TTS 任务，`firstframes\plot_grids_v2\` 是宫格首帧的脚本

脚本里的绝对路径已按新布局改写，但**改完没有重跑过**。改写依据是 `projects\猎奇\logs\legacy-migration-manifest.csv` 和 `legacy-migration-moves.log`，覆盖各时期的写法（`video\lieqi\tudou`、`legacy-source\lieqi`、box 上的 `/workspace/lieqi/...`）。另外几项统一替换：
- `comfy-stills` 改成 `shared\runtime\engines\stills-runtime`
- GPU 锁改成 `shared\work\cache\gpu.lock`
- runner 的根目录 `video\lieqi` 改成 `projects\猎奇`，所以运行日志会写进 `projects\猎奇\logs\`

基于 `BASE` 拼的相对路径也一起改了：
- v3 镜头片段指向 `video\clips\`，配音指向 `audio\vo_seed42_v2\`
- 首帧表指向 `image\plot_grids_v2\frame_map_v3.json`，分镜指向 `storyboard\`
- 成片和封面分别写进 `video\` 和 `image\`；v1 的这些路径指向 `archive\`
- 口型试点指向 `drafts\tudou-lip-pilot-ltx\`

`frame_map_v3.json` 是数据文件，在 `episodes\tudou\image\plot_grids_v2\`，路径也一起改了，旁边留了改之前的 `frame_map_v3.json.bak-20261008`。

## 已知没解决的引用

1. 三个 `i2v\run_lieqi_i2v*.py` 原来从 `C:\Users\10060\AppData\Local\Temp` 导入 `i2v_cmp`。Temp 里那份已经清掉了，现在改成从本目录 `tudou\i2v\` 导入同名模块。注意这一份和 `shared\work\scratch\legacy-root\i2v-cmp-2026-10-01\i2v_cmp.py` 的 md5 不一样，当时 Temp 里到底是哪一版已经查不到了。
2. `i2v_cmp.py` 里默认的 `SCR` 还是 `shared\work\scratch\legacy-numbered\i2v-cmp-2026-10-01`，这个目录已经不存在了。各个 runner 都会覆盖 `m.SCR`，所以暂时没影响，这一处没改。
3. v1、v3 两个 i2v runner 的工作目录（`SCR`，放 in/out/temp）还是集目录下的 `i2v\`、`i2v\v3\`。原来的 in/out 都是重复件，已经删掉了，重跑时会重新创建这两个目录。日志和 results 已经改指 `logs\i2v_v1\`、`logs\i2v_v3\`。
4. `scripts\tudou-refs-v1.json` 的 `raw_dir` 还是 `E:\program\1project\video\lieqi\tudou-tuihun\raw\tudou-refs-v1`。这是首轮参考图的输出目录，legacy 里没有对应的文件，映射不到，所以没改。
5. `tudou\firstframes\plot_grids_v2\` 下面的脚本原本是在 box 上跑的，依赖 box 的字体（`/usr/share/fonts`）、`/workspace/kepu-pipeline` 和生图 API。路径已经改成 ddbbi 的路径，但要重跑还得先把这些依赖换掉。
6. `/workspace/kepu-pipeline` 这类 box 路径都没改。
7. `voice\run_prepare_voice_packages.ps1` 用的 `shared\runtime\engines\tts\hf-cache` 现在不存在（`modelscope-cache` 是在的），没改。
8. 有几处运行时才生成的路径现在还不存在：`logs\voice\seed42_v2.exit`、`drafts\tudou-lip-pilot-ltx\logs\v3_lip_pilot.exit`、`image\plot_grids_v2\frame_map_v3_ready.flag`、`archive\audio\seed42_all\`（这是 `seed42_all_jobs.json` 的输出目录，原来就是空的）。
9. `dy.py`（写死了抖音 cookie 的抓取脚本）已经登记成废稿删掉了，没有迁过来。
