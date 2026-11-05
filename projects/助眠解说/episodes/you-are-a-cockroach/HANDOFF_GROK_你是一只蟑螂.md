# Grok执行交接：《你是一只蟑螂》

## 持续执行要求（2026-10-09）

本交接允许Grok自主处理技术实现和可修复异常，不需要逐镜冗余失败预案。创作方向遵守锁定分镜与镜头白名单。普通阶段完成后直接进入下一阶段，不因阶段结束或常规错误等待用户催促。每个任务结束/阶段切换，更新既有manifest及简短续跑记录（当前阶段、已完成项、在跑PID/请求、下一命令、阻塞原因）。中断后核对实际进程与文件，从未完成项续跑，不重复提交运行中任务、不重做合格资产。等待GPU时推进独立CPU工作。只有无法自行解决的真实阻塞才报告，不把普通检查点当停止条件。详细规则：`E:/program/1project/video/rules/助眠解说/execution-continuity.md`。不保证平台不会打断会话，依靠落盘状态恢复；不以一句“后台继续”代替可追踪进程。

## 最新视觉筛选（2026-10-09，覆盖旧候选组合）

用户测试后淘汰画面慢放和所有正逆放。只用V1原速动态、V3原速动态+尾帧推拉、V5-C一次叠化循环、V7-C一次叠化循环+尾帧推拉、P1图片单方向运镜、P2图片单方向运镜+终点停留。尾帧参考2–3秒、优先小于4秒且不超过原生片长；图片不往返。完整约束以 `rules/助眠解说/visual-motion.md` 为准。当前主要反馈为零星中间帧虚化，先排查raw与叠化/修复，不新增逐帧清晰度、光流或自动删帧门禁，不增加逐镜用户审批；优化无明确收益则继续现有生产。此处不使用画面慢放，配音atempo=0.7304照常执行。

## 最新音频变更（2026-10-08，优先执行）

用户已将BGM提高三成（线性增益×1.30，即+2.279dB），配音速度调整为当前的0.83倍。旧raw处理因子0.88现更新为 `atempo=0.7304`，片头与正文统一；已处理0.88音轨仅额外乘0.83，禁止双重降速。参考总时长更新为54–68分钟，实测为准。重新生成全部音轨时间轴、字幕、分镜切点与片头分钟数。规则真源：`E:/program/1project/video/rules/助眠解说/audio-pace.md` 和 background-music.md；本集具体BGM新参考响度见audio/AUDIO_LOCK.md。该更新不改变TTS声线、seed或引擎，也不自动给片头加BGM。

## 任务与授权

2026-10-09新增镜头规则：图生视频与图生推拉视频仍按来源分两类、互不混用。两类均可按实际旁白选择自身尾帧停留/推拉来延长，非必需，整镜分类不变。优先按本集visual/PRODUCTION_PLAN.md和共享助眠visual-motion.md执行；不再机械地为每个时长窗口补一次动态生成。记录类别、尾帧延长秒数和实际模型动态播放秒数，分别统计；动作未完成、尾帧不清楚或延长拖沓时换镜/补新素材。下面关于短片窗口的数量为旧估计上限，按此规则重算；禁止循环填充的要求仍有效。

为“星夜慢谈”制作完整40分钟以上助眠科普成片。用户已选择“Codex锁定文稿与音轨方案，Grok全程执行”，本集不再等待默认的逐阶段用户审批。可以自主完成本地配音、全量新图片、真实视频、高清修复、剪辑、字幕、片头、横竖封面与最终质量检查。发布账号、对外发消息、清理旧资产未授权。硬阻塞如凭据缺失或服务收费无法确认时如实报告，不伪造完成。

这是新集全量制作，不是地磁任务重跑。旧地磁仅作为已验证技术参考，不复制图、字幕时间轴或旁白。当前没有本集GPU任务运行；本交接产物为文案及方案，不能接手时当作已完成媒体。

## 唯一项目根目录

`E:/program/1project/video/projects/助眠解说/episodes/you-are-a-cockroach`

先依次读取以下文件：

1. `story/NARRATION_MASTER.md`：唯一口播真源；不扩写缩写。
2. `audio/AUDIO_LOCK.md`：声线、时长、分钟数、混音与字幕。
3. `visual/PRODUCTION_PLAN.md`：全量视觉、试点、清晰度、回退和成本。
4. `visual/SHOT_PLAN.json`：168正文分镜+8片头图，90真实视频候选；时间锚定已处理音轨。
5. `visual/ALL_SHOT_PROMPTS.md`：每镜图片及动态提示词，均已提供。
6. `story/FACT_NOTES.md`：不得突破的科学边界。

以上相对路径全部相对于本项目根。规则真源在 `E:/program/1project/video/rules/助眠解说/`，优先读 intro-node.md、background-music.md、visual-motion.md、covers.md、account-identity.md；共享美术规则在 `E:/program/1project/video/rules/shared/memory/sleep-aid-visual-style.md`，其他共享入口为 image-grid-generation.md、video-workflow.md。本集授权覆盖共享人工审批/先图后音顺序，仅对本集生效，不修改全局规则。

## 第0步：可恢复记录

先将 `PROJECT_STATE.json` 中 execution_state 从not_started改为running，创建本集 `runs/<日期批次>/`，日志、manifest、临时文件都留在E盘本集目录。每个资产使用稳定id，记录输入哈希、prompt、实际模型/参数、输出路径、耗时、费用、验收证据、失败原因。状态只用 planned/running/generated/pending_review/passed/failed/fallback/blocked，不把自动检查通过写成人工验收。

执行本集预检（仅文本，不占GPU）：

```powershell
python 'E:/program/1project/video/projects/助眠解说/episodes/you-are-a-cockroach/prepare_handoff.py'
```

预期：87个段落、157个配音段、156可执行、1分钟数占位、168正文分镜、8片头图、90动态候选，文字重构一致。该脚本重建计划文件，不生成媒体；进入制作后不要拿它覆盖补充过的运行manifest。需要重新运行时先备份修改过的计划。现有 `PREFLIGHT.json` 是文本检查结果，不能当媒体验收。

## 第1步：正式音轨优先

先用当前b2参数生成bridge、8章、outro和片头前两句。按 `audio/jobs/<章节>.json` 分章运行。引擎兼容性已按当前gen_shots.py字段核对，但未跑TTS；任何环境问题先用短段验证。

GPU执行必须先读 `E:/program/1project/video/shared/gpu-queue/README.md`，提交本集请求并获得granted；队列管理线程为 `01a10e62-835a-78b2-8c7b-6d79e97ce195`。不得自授予，不继承地磁一次性免队列授权。共享锁 `E:/program/1project/video/shared/work/cache/gpu.lock`，旧保护锁 `E:/program/1project/video/shared/runtime/comfy/cache/gpu.lock`。VoxCPM run_shots.ps1只是等待锁，不会获取独占锁；执行者须用当前队列规定的锁包装器取得本任务锁，不删他人锁。

获得队列时段且有实际独占保护后，引擎调用形状如下，示例不是已完成任务：

```powershell
& 'E:/program/1project/video/shared/runtime/engines/tts/voxcpm/.venv/Scripts/python.exe' 'E:/program/1project/video/shared/runtime/engines/tts/voxcpm/gen_shots.py' 'E:/program/1project/video/projects/助眠解说/episodes/you-are-a-cockroach/audio/jobs/bridge.json'
```

runner不自动跳过已有WAV，断点续跑用第二个参数传逗号分隔缺失id，禁止重跑整章覆盖合格音频。需保留不同take时修改新jobs的out_dir，旧take不动。

门禁入口 `E:/program/1project/video/shared/runtime/envs/vo-gate/kepu-pipeline-box/scripts/vo_gate.py`，Python用同TTS venv；PYTHONPATH为 `E:/program/1project/video/shared/runtime/envs/vo-gate/pylibs`，MODELSCOPE_CACHE为 `E:/program/1project/video/shared/runtime/envs/vo-gate/modelscope`。登记profile源为 `E:/program/1project/video/assets/助眠解说/voices/b2-warm-male/vo_gate/profile_b2_registry.yaml`，复制到本集并修复遗留E:/ComfyVideo路径，语音基准不改。对当前CLI先读help，gate输入使用 `audio/gate/<章节>-shotlist.json`、本章raw目录、本章final/out目录与对应base-jobs，remote none。声线门禁仍需GPU排期，不绕锁。

生成处理后时间轴 `audio/timeline.json`，含utterance、paragraph、chapter的start/end/duration与实际文件；正文至少2400秒。先查漏段与裁切，不补无意义静音。再用真实正文时长解析片头第三句，测总时长复核分钟数。最终稿另存 `story/NARRATION_RESOLVED.md`，原模板保留。第三句所讲主题与艺术字《你是一只蟑螂》同为蟑螂演化史，不改成其他主题。

## 第2步：所有新图

按音轨段落锚定分镜；每镜用已给提示词生成，图文对应必须验。森林不是一张图重复四十分钟。按SHOT_PLAN指定single/2x2_tile执行，先做少量跨章节图片确认风格与虫体结构，再按章批量完成。2×2每格完整独立prompt，切分保存像素尺寸与原图。严禁PPT、教程图、箭头、术语标签、文字直接生到图内。科幻感通过空间、灯光和材质提升，保持虫体正常。

生图读取当前共享配置中的批准模型和私有凭据。不得写出密钥。图片批次只以磁盘路径、manifest、低清联系表与文字QA交接，避免把所有原图载荷灌入长期聊天。所有图片必须本集新做；不复用地磁图。

## 第3步：6个真实视频试点，再按章生产

试点id见SHOT_PLAN的pilot_shots。每个只做一段约6–8秒，记录真实生成耗时、费用、帧率、分辨率和结构风险。只对明确可修问题最多再尝试一次，不无限排队。先验证VSR 3帧smoke，再完整试点。按实测计算全量预算/工时，不报猜测成本。

试点通过后逐章生成90个候选分镜需要的独立动态窗口；不要求全部成功。主体走动、触角、雨水/叶片微动是实际动态；affine只能记作静图运镜。不能用慢放一段、倒放或重复循环冒充多个视频。超过计划窗口上限时，新增关联静帧补足，不改变稿件。若试点显著失真，停止扩大同类型动态，保留失败并fallback。依赖等待期间可继续CPU剪辑或云端生图，不抢本地GPU。

## 第4步：高清修复与验收

运行说明：`E:/program/1project/video/shared/video-restoration/VSR_WORKFLOW.md`。入口run_vsr_streaming.py与qa_single_vsr.py在同目录；Python为 `E:/program/1project/video/shared/runtime/comfy/installs/portable/python_embeded/python.exe`。dry-run不加载模型，正式修复也须队列granted与该runner自身锁管理。输入/基线/全新输出目录/shot-id均使用本集绝对路径，不照抄文档地磁示例。

每段保存raw、同构图1080p Lanczos基线、VSR候选和QA。非16:9输入等比裁切/留边，不拉伸。自动QA无失败仍是pending_review；实际播放确认后才记录有证据的验收。争议画面一律保留、列表告知用户，正式版本默认高清静帧affine。清晰度、解剖结构、时序三者同时满足才采用真实视频。

## 第5步：片头、整片与封面

沿助眠op4片头规则使用实际三句VO切点，做错峰四格→格子放大全屏→叠化连续景别→主题艺术字。参考代码只读：`E:/program/1project/video/shared/workflows/助眠解说/b-geomagnetic-reversal/intro/pilot-grok-op4-vo/build_op4_vo_A.py`；适配新集并放本集，不能执行旧路径覆盖地磁。片头无BGM，接半分钟故事由来，再接“你睁开眼”，不重复引入。

混入统一BGM，按实际处理后音轨做字幕。章节逐段先渲染验证，最终拼成一部完整电影式视频，不只交零散短片。1920×1080、30fps、SAR1、H.264高质量（CRF16–18参考）、AAC256k；VFR输入先规范时间基准。尽量一次最终编码，不反复有损转码。分别输出clean与sub版本，字幕字体来自本集字体文件。横竖封面分别排版，正文仍是横屏，不把横图拉成长条。

## 完成定义

- `delivery/你是一只蟑螂_1080p_clean.mp4` 和 `delivery/你是一只蟑螂_1080p_sub.mp4`，完整40分钟以上（实测）。
- `delivery/narration-dry.wav`、`bgm-stem.wav`、`mix-master.wav`、SRT、ASS、字体/许可清单。
- 横竖封面、标题/简介/标签文本；不自动发布。
- 全量资产manifest与时间轴，实际真实视频镜头数和播放时长占比，动态失败/回退/待验镜头列表。
- ffprobe、完整解码、音画时长检查、字幕越界/缺字检查、循环接缝检查、片头与所有章节关键镜头实际播放记录。音频首尾/章界抽听，禁止静音空段或漏段；整片未看不能写全片看过。
- 配音文本拼回锁定稿一致，未朗读编号；本集引入不重复，分钟数匹配实测，图片均横屏/匹配口播，无大量复用。

最后更新PROJECT_STATE，所有必需文件存在且硬检查通过才能写produced；视觉或听验未完成写pending_review，不伪造用户验收。只把最终成片路径、封面路径、质量报告和争议清单交给用户。失败阶段保留日志和已有合格素材，从manifest恢复，不把全部素材重新生成。
