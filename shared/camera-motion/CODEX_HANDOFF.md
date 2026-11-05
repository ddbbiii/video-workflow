# Codex 交接：静帧运镜 Blender 后端（Grok 已交付，待复核）

本文是 `GROK_HANDOFF.md` 的回执，接着 `CODEX_TODO.md` 里「我负责的接入与复核」往下做。所有路径都在 ddbbi，工作区 `E:\program\1project\video`，PowerShell 5.1，没有 git。

## 1. 交付了什么

只改了 `shared\camera-motion\` 目录；改动前的原文件都备份成 `*.bak-20261006`。

| 文件 | 状态 | 作用 |
|---|---|---|
| `blender_backend.py` | 新增 | 解析 Blender 路径，导出逐帧轨迹，无界面调用 Blender，PNG 帧缓存，用与 affine 相同参数的 FFmpeg 编码；走 EEVEE 时占 GPU 锁 |
| `blender_scene.py` | 新增 | 在 Blender 里运行的场景脚本：正交相机 + Emission 纹理平面，逐帧读取预先导出的轨迹 |
| `camera_motion.py` | 修改 | 新增 `backend:"blender"`；默认仍是 affine；缺 Blender 或未知 backend 直接报错，不静默回退；共用 `progress` / `view_at` |
| `compare_backends.py` | 新增 | 成对渲染、ECC、并排视频、`QA_REPORT.json/md` |
| `test_camera_motion.py` | 修改 | 新增未知 backend、缺 exe 硬失败、Blender 冒烟、UV 角标测试 |
| `README.md` | 修改 | Blender 用法与限制 |
| `verify_motion.py` | 未改 | 契约兼容 |
| `testdata\` | 新增 | `make_testdata.py` 可复现生成；`MANIFEST.json`；棋盘（带坐标和四角标）、小字、星点、岩层，横竖各一；两张真照片只读拷贝 |
| `testdata\configs\` | 新增 | 6 对 affine/blender 验收配置（共 30 镜），除 backend 外完全相同 |
| `testdata\GPU_LOCK_NOTES.md` | 新增 | GPU 锁说明 |

Blender：官方便携版 4.5.14 LTS，`E:\program\blender\4.5.14\blender-4.5.14-windows-x64\blender.exe`（zip 在 `E:\program\blender\`）。没改 PATH，没装系统安装包。源码里没有写死本机路径，通过 `--blender` 或环境变量 `CAMERA_MOTION_BLENDER` 指定。

## 2. 怎么跑

```powershell
$py = "E:\program\language\python\Python-3.11.0\python.exe"
$env:CAMERA_MOTION_BLENDER = "E:\program\blender\4.5.14\blender-4.5.14-windows-x64\blender.exe"
cd E:\program\1project\video
& $py -m unittest discover -s shared/camera-motion -p "test_*.py"
& $py shared/camera-motion/camera_motion.py <plan.json> --out <新运行目录> --blender $env:CAMERA_MOTION_BLENDER
& $py shared/camera-motion/verify_motion.py <运行目录>
& $py shared/camera-motion/compare_backends.py --run-dir <目录> --blender $env:CAMERA_MOTION_BLENDER --pairs matrix_land_same,matrix_port_same
```

渲染设置：Cycles CPU，1 spp，`--factory-startup`（本机用户配置里挂了 Blender AI MCP 插件，会开 8765 端口，必须用 factory 启动避开）；色彩 Standard；无 motion blur；编码 libx264 CRF18 yuv420p。Cycles CPU 不占 GPU 锁；只有改用 EEVEE 才占 `shared\work\cache\gpu.lock`（格式 JSON `{owner,pid,started}`）。

## 3. 已验证的结果

- 单元测试 8/8 通过。
- 完整报告：`shared\camera-motion\runs\20261006-blender-qa\QA_REPORT.md` 和 `.json`，30 条并排视频在同目录各个 `*_compare\`。
- 真实项目 batch02（助眠地磁五镜）：输出在 `projects\助眠解说\legacy-source\zhumian\b-geomagnetic-reversal\gen_rebuild\runs\20261006-camera-motion-backend-cmp\`，并排视频在其中的 `compare\{earth,cutaway,needle,outcrop,cave}_sbs.mp4`。两个后端五镜都 pass，Blender 残差 rms ≤ 0.008。耗时 affine 约 31s，Blender 约 362s。
- 性能：Blender 每帧 0.18–0.29s，墙钟约为 affine 的 11–15 倍。
- 颜色：编码后 mean|ΔRGB| 约 2–3.6（含 H.264 误差）；PNG 静帧探针在 Standard 下可到 0/255。
- 当前建议：affine 保持默认，Blender 作可选后端。用户还没有播放签字。

## 4. 需要你接着查的问题（按优先级）

1. **横屏推/拉残差系统性偏高**。`matrix_land_same` 的 push/pull 四镜 Blender rms 都在 0.094–0.096，被标 indeterminate；而 `matrix_port_same` 的 push/pull 只有约 0.004–0.005。数值太整齐，**假说**：横屏下 `ortho_scale` 宽高取值、像素中心半像素约定或 sensor fit 有一处与 affine 不一致，造成随缩放线性累积的偏差。先用棋盘逐帧对比 Blender 与 affine 的 PNG（不经编码）定位，修好后重跑矩阵。
2. **组合运动残差 0.11–0.15**（land_same、port_same、cross 两组的 combo 镜都超 0.08，相关度仍 >0.99）。可能和第 1 条同源，先修第 1 条再看。
3. **星点**：Blender 的 ecc_min 约 0.89，affine 约 0.99。查 1 spp 下点状细节的纹理过滤和采样（Closest/Linear/Cubic、像素滤波宽度），用实际对照定参数，不要靠加模糊掩盖。
4. **小字**：两个后端都 indeterminate（rms 8–30，ecc 0.42–0.62），说明是 `verify_motion.py` 对小字纹理测不准，不是后端问题。需要决定是换 ROI 还是接受为不确定。
5. **相对 source 路径**：把 plan 复制到别的目录运行时，相对 `source` 会解析错位。batch02 当时临时改成了绝对路径。应改为始终相对原 plan 文件所在目录解析，或在复制时重写路径。
6. Blender 启动有 TBBmalloc 警告，目前没发现影响。
7. 每帧耗时：可测 Cycles GPU（OptiX）或 EEVEE 是否能把 10–15 倍压下来；改用 GPU 必须走锁。

## 5. 边界

- 修改只限 `shared\camera-motion\`；运行资产写新目录；不改生产规则、声线、文案、旧图、原配音；不迁移全片，用户确认前默认后端不变。
- 不要删除任何东西。现有 `runs\` 下 PNG 帧缓存约 5 GB，删除要先经用户同意并登记到 `/workspace/kepu-pipeline/DISCARDS.md`（由「视频号规划」维护）。
- 编辑现有文件前先备份；不 git reset / checkout。
- 数值 QA 只是局部检查，不等于肉眼无抖动；结论写清测量方法和不确定性，验证不了的标「未验证候选」。
- 后续独立任务（分层视差、内容动画、长任务资源控制）见 `CODEX_TODO.md`，不属于本轮。
