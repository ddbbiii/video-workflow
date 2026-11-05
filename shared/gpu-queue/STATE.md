# GPU 调度状态

## 当前覆盖指令（2026-10-13）

- 用户明确要求 GPU 队列暂时废弃，所属会话直接执行。以下历史排队与 grant 约定暂不生效；不得自动重新启动旧 queued 请求。直接执行仍需检查实际占用，避免资源冲突。
- `sleep-intro-sentence-voice-preview-20261012` 已退出队列，由总调度直接执行。

## 定时任务

- gpu：ACTIVE，每十五分钟检查；队列清空后暂停。

## 调度策略

- 队列由管理助手自主推进：显式优先级优先，未指定优先级按提交时间排序。
- 所属会话在排队、获准、启动和运行期间默认静默；完成、失败、取消或必须人工确认的阻塞时才主动通知。
- 所属会话主动修改任务信息后，管理助手按新信息重新排序或重新检查依赖。

## 最新调度

- 2026-10-07 17:20（+08:00）：助眠解说代管的 3 个请求已全部 completed：zhumian-geomag-v3-esrgan-stills（14:57:06–14:57:52）、zhumian-geomag-v3-i2v-ltx（14:58:26–15:59:22，12/12 镜）、zhumian-geomag-v3-vsr-i2v（16:00:22–16:55:38，c04 验证 1 次通过 + 7 镜）。各自占锁、跑完放锁，当前两处锁均不存在。注意：camera-motion/blender_backend.py 的锁路径解析为 E:\program\1project\video\work\cache\gpu.lock（不是 shared\work\cache\gpu.lock），与 VSR runner/README 的主锁不一致，需管理线路统一。
- 2026-10-07T14:56:28+08:00：zhumian-vsr-baseline-c04-streaming-retry4-20261007 → failed（进程消失：PID34164 不存在、两处锁均无、显卡空闲；raw mp4 缺 moov 头为半截文件，原样保留）。由助眠解说线路经老大授权代管收尾。
- 老大 2026-10-07 授权助眠解说线路自行代管其 GPU 请求（不再等待管理聊天）：zhumian-geomag-v3-esrgan-stills / i2v-ltx / vsr-i2v 按此顺序依次 granted 并执行，执行方自行占锁/放锁并回写终态。
- zhumian-vsr-baseline-c04-streaming-20261007：failed，首个7帧分块因输入CUDA与模型CPU设备不一致退出，未产出VSR视频；日志shared/video-restoration/vsr-streaming.stderr.log，源视频/Lanczos/旧失败目录保留。
- zhumian-vsr-baseline-c04-retry3-20261007：failed，RealBasicVSR推理阶段CPU输出分配失败（尝试分配2422210560字节），未产出VSR视频；日志shared/video-restoration/vsr-retry3.stderr.log。进程已退出，GPU锁需核实释放；原始/Lanczos/旧失败目录保留。
- zhumian-vsr-baseline-c04-retry2-20261007：failed，portable环境已通过cv2/torchvision/simplejson，但ModelScope继续缺少sortedcontainers，未产出VSR；日志shared/video-restoration/vsr-retry2.stderr.log，锁已释放。原始视频、Lanczos基线及旧失败目录未改动。
- zhumian-vsr-baseline-c04-retry-20261007：failed，已用portable Python启动并通过cv2/torchvision检查，但ModelScope初始化缺少simplejson，未产出VSR；日志shared/video-restoration/vsr-retry-c04.stderr.log，原始/Lanczos/上一轮失败目录未改动。
- zhumian-vsr-baseline-c04-20261007：failed，ModelScope管线初始化缺少opencv-python与torchvision，未产出VSR视频；日志shared/video-restoration/vsr-test01.stderr.log，锁已释放。原始视频与Lanczos基线保留，需补齐运行环境后由线路决定是否重试。
- 05:16:37：cinematic-retry-c04已completed，121帧/24fps，原始/720p/1080p均decode_ok；进程退出、服务关闭、锁释放。视觉QA pending_playback。VSR runner尚不存在，保持queued/hold等待线路准备。

- zhumian-vsr-baseline-c04-20261007：queued/hold，cinematic-retry-c04已completed；RealBasicVSR runner 已建立、输入目录已指向 retry-c04、权重已缓存，等待管理助手按 GPU 队列放行；仅处理ch1-c04-v2-01。原始视频与Lanczos基线保留。
- 2026-10-07：按用户最新计划，VSR 先只执行单镜头 `ch1-c04-v2-01`；请求 `zhumian-vsr-baseline-c04-retry-20261007` supersedes 首次失败请求，使用 `shared/video-restoration/run_vsr_test01.ps1` 的 portable Python，其他镜头暂不排队、不扩展。
- 2026-10-07：retry 请求因 portable ModelScope 缺少 `simplejson` 在模型初始化前失败，GPU 锁已释放且无输出视频；已补装 `simplejson`，新请求 `zhumian-vsr-baseline-c04-retry2-20261007` queued，使用独立脚本和输出目录，仍只处理 `ch1-c04-v2-01`。
- 2026-10-07：retry2 又因缺少 `sortedcontainers` 在模型初始化前失败，GPU 锁已释放且无新输出；已补装并通过 `pip check`，新请求 `zhumian-vsr-baseline-c04-retry3-20261007` queued，继续只处理 `ch1-c04-v2-01`。
- 2026-10-07：retry3 已进入 RealBasicVSR 推理，但 ModelScope 在将完整 4×输出一次性搬到 CPU 时申请约 2.42GB 失败；已创建流式 runner，按 7 帧分段推理并即时写盘，提交 `zhumian-vsr-baseline-c04-streaming-20261007`，仍只处理 `ch1-c04-v2-01`。
- 2026-10-07：streaming 首次运行因 runner 将输入送入 CUDA 而模型权重仍在 CPU，设备不一致失败；已改为显式将模型和输入放到同一设备，提交 `zhumian-vsr-baseline-c04-streaming-retry4-20261007`，仍只处理 `ch1-c04-v2-01`。
- zhumian-real-video-cinematic-test01-20261007：failed，04:39:31首镜文本编码阶段ComfyUI退出，无manifest；PID18700/48184已退出，两处锁已释放。VSR继续等待依赖完成。四镜真实LTX-2.3图生视频测试；不使用affine。输出：projects/助眠解说/legacy-source/zhumian/b-geomagnetic-reversal/gen_rebuild/runs/20261007-ltx-cinematic-test01；完成后核实manifest、日志、进程退出并回报所属会话。已修正脚本共享锁模块导入路径。
- mirror-mature-acd-20261006：completed，16:20:58单线程加载重试完成；A13.44秒、C12.96秒、D13.92秒，manifest均48kHz/decode_ok。PID27892已退出，无Python/Blender进程，两处锁为空，名额已释放。首轮崩溃日志保留；年龄与句间自然度待用户试听。当前无待执行请求。
- mirror-voice-test-20261006：completed，14:39:56完成；manifest与日志记录13.92秒、48kHz连续试听音频。PID52392及父进程8492已退出，两处锁均不存在，服务均离线，GPU名额释放；试听验收由悬疑线路处理。当前无 queued/granted/running 请求。

## 历史调度（2026-10-06 14:10）

- batch02：已核实四条 manifest decode_ok、完成日志09:40:32、进程退出、服务关闭；调度助手已修正为 completed 并释放名额，视觉 QA 仍 pending_playback。
- mirror-who-are-you-i2v-v0.3：completed，两段生成并通过解码检查，12:41:28 完成；PID 7628 与 H3 服务已退出，锁已释放。视觉 QA 由线路 CPU 处理。
- xuanyi-voice-design-20261006：completed，12:45:02 GEN END exit=0，ALL DONE；PID46800及生成进程已退出，锁已释放。
- 当前无 queued/granted/running 请求；未发现 Python/Blender 进程，两处共享锁均不存在，8188/8189/8191 服务均离线。GPU 采样63%，显存9247/16311 MiB；整机占用不等同于队列生成任务，后续放行前重新核实可用资源。候选音频验收由悬疑线路处理，不自动进入正文。
- 主动检查并推进队列，不等待用户催促；完成生成不等于视觉 QA 或正文批准。

## 接管时快照（2026-10-06，非实时状态）

- H3 A/B/C 测试批次已完成：A/B/C 均 success，MANIFEST 于 2026-10-06 08:14:41 完成，GPU 名额已释放。
- 批次脚本：`shared/project-tools/grok-bot-overnight/bench_h3_node_abcs.py`，观察到 PID `24212`。
- H3 服务：`127.0.0.1:8189`，观察到 PID `44620`。
- 观察到运行 prompt：`a2cf35b2-6a37-4ca5-a238-e4a2f3758be3`，输出前缀 `h3-node-ab/A-864-easycache`。
- 最新检查：用户要求启动 batch02 后已停止空闲 H3 服务 PID `44620`；8189 已关闭，RTX 5060 Ti 约 30% 利用率、4122/16311 MiB；共享 GPU 锁不存在。助眠助手仍需重新做启动前检查。
- ComfyUI 服务仍在运行并保留约 4 GB 显存；这不等于有 GPU 任务在执行。

## 当前队列

- `zhumian-real-video-batch01-20261006`：`cancelled`，助眠线路；08:27 按用户要求停止，PID `33060`/ComfyUI `21632` 已退出。旧请求不重新放行，等待新的请求 ID。
- 批次已启动本地 ComfyUI 8191（子进程 PID `21632`）；首个 `ch2-c03` 已提交 prompt `1adbbe64-b442-496c-842a-fcfb6d24efda`。
- 任务范围：LTX-2.3 横屏真实图生视频样片（ch2-c03/c04/c08、ch3-c07），预计 45 分钟，估算显存 15000 MB。
- 请求文件：`shared/gpu-queue/requests/zhumian-real-video-batch01-20261006.json`；当前仅登记，未启动。
- `mirror-who-are-you-i2v-v0.1`：`completed`，S04/S21 均生成但动态 QA 拒绝正式使用（S04扩展出新浴室全景，S21凭空增加手持手机）；正式版本回退高清静态图+affine，未登记批准 hash，未进入正文。PID `32068` 已结束，08:54 释放名额。
- 任务范围：先以 affine 默认筛选 S04/S09/S12/S21，仅对确有自然运动必要且不损失清晰度的少量候选做 H3 I2V 草稿；争议时回退 affine；S24 暂不做 I2V，不把四个镜头视为硬性全量生成。
- 依赖：`h3-node-ab-test-20261006` MANIFEST 完成；预计 30 分钟，估算显存 15500 MB。
- 请求文件：`shared/gpu-queue/requests/mirror-who-are-you-i2v-v0.1.json`。
- 放行前已重新检查 H3 MANIFEST complete、8189 队列为空、8191 已退出、GPU 锁不存在。

- `zhumian-real-video-batch02-20261006`：`running`，助眠线路，提交助手 `01a10af6-0138-7ef0-8236-323efe9fd231`；09:02 启动，PID `36284`，子 ComfyUI 8191 PID `5016`。首个 `ch2-c03` 已提交 prompt `e3ae69f9-9558-4c6c-b654-1400861f4d52`。日志：`projects/助眠解说/legacy-source/zhumian/b-geomagnetic-reversal/gen_rebuild/runs/20261006-ltx-real-video-batch02/batch02-run.log`。当前 GPU 约 97%，13856/16311 MiB。
- 请求文件：`shared/gpu-queue/requests/zhumian-real-video-batch02-20261006.json`；不要重新放行已取消的 batch01。
- `mirror-who-are-you-s04-i2v-v0.2`：已取消并移除请求文件，不执行。改由 v0.3 统一处理 S04/S21。
- `mirror-who-are-you-i2v-v0.3`：`queued`，悬疑动漫线路，提交助手 `01a10af5-7adb-71c0-82f4-641572aec029`，09:10 提交，排在正在运行的 batch02 之后。S04/S21 均先不变形裁成 864x480 横屏，72 帧、24fps、EasyCache 开，串行生成；不得竖屏、拉伸、凭空增加手机或改变镜面几何，失败回退 affine。

上述 PID 与指标需在下一次放行前重新核对；不得凭此快照终止进程或删除锁。

- 2026-10-08 06:32（+08:00）：zhumian-geomag-intro-op4-vo-tts-20261008 completed（06:31:15–06:32:21，助眠解说自管，占 shared\work\cache\gpu.lock，结束即释放）。

- 2026-10-08 07:19（+08:00）：zhumian-geomag-full-r1-tts-20261008 queued（助眠解说自管，4 句 b2 口播；GPU 空闲时即放行）。
- 2026-10-08 07:23（+08:00）：zhumian-geomag-full-r1-tts-20261008 completed（07:23:00–07:23:37，助眠解说自管，占 shared\work\cache\gpu.lock，结束即释放；07:19 首次运行因会话断开中断，已自行清除本任务残留锁后重跑）。

- 2026-10-08 07:41（+08:00）：zhumian-geomag-full-r1-nvenc-20261008 queued（助眠解说自管，地磁全片 NVENC 编码；锁空闲即放行）。
- 2026-10-08 07:52（+08:00）：zhumian-geomag-full-r1-nvenc-20261008 completed（助眠解说自管，占 shared\work\cache\gpu.lock，结束即释放）。

- 2026-10-09 16:23（+08:00）：zhumian-cockroach-tts-20261008 completed（助眠解说自管，占 shared\\work\\cache\\gpu.lock，结束即释放；raw wav=156）。

- 2026-10-10 14:58（+08:00）：zhumian-octopus-tts-20261010 queued→granted（助眠解说自管，章鱼口播280段）。


- 2026-10-10 15:44（+08:00）：zhumian-octopus-tts-20261010 completed（助眠解说自管，raw wav=280）。
