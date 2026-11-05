# Grok 执行指导：先出可审草稿，再完成整片

## 任务

继续执行《你是一只蟑螂》当前项目。静帧、156段处理后口播、90条 I2V 和86条 affine 已存在；不要重新生成这些资产。目标是从现有文件生成可审章节草稿，并完成 clean/sub 整片。

项目根目录：
`E:\program\1project\video\projects\助眠解说\episodes\you-are-a-cockroach`

先阅读：

- `HANDOFF_GPT_当前进度_20261010.md`
- `OPTIMIZATION_PLAN_20261010.md`
- `HANDOFF_GROK_你是一只蟑螂.md`
- `audio/AUDIO_LOCK.md`
- `visual/SHOT_PLAN.json`

## 必须按此顺序执行

1. 创建新的 `runs/<日期>-assembly-b01/`，不要覆盖任何旧 run。
2. 读取处理后口播 manifest，生成实际时间轴 `timeline.json`。以音频实际秒数为准，不按字数猜时长。
3. 读取 SHOT_PLAN、I2V manifest 和 affine manifest，生成 `media-map.json`。I2V lanczos 优先；路径缺失、结构明显异常或无法解码时回退对应 affine。
4. 先算每镜目标秒数与实际媒体秒数差。I2V不能覆盖且没有锁定延长方案时，整镜回退对应原图，按最终镜长重渲染P1；不在同镜接原图补足。7秒affine不够长时也重渲染，不能循环充数。随后按章节拼草稿。允许 `visual_qa=pending` 的 I2V 进入草稿，但在 manifest 中保留 `pending_review`，不能写成 `passed`。
5. 先并行准备BGM stem、混音预览和affine需要的章节媒体；字幕分为两步：可审草稿可用utterance边界，但正式字幕必须等片头接入、最终旁白混音和全片timeline锁定后统一生成。正式字幕使用完整纯旁白stem和锁定文稿的实际发音边界，不把长句拆行后平均分配时间。
6. 根据正文实测秒数运行片头 resolve，再接入片头。片头无 BGM；正文 BGM 使用 `SLEEP-BGM-UNIFIED-001`，按既定增益 ×1.30。
7. 完成章节级解码、音画时长、分辨率、黑帧检查后，再做一次整片 clean/sub 编码。
8. 写 `FINAL_QA.json`，区分自动检查、待人工复核和回退镜头。

首个章节完成后验证配置，立即继续其他章节，不等待用户审批。最终高清处理沿既有要求：Lanczos允许用于草稿，不能因赶工默认替代已要求的修复版。仅对时间轴最终选中的动态跑VSR，不修复未使用候选。

## 并行执行要求

不要按“时间轴完成后才字幕、字幕完成后才混音、混音完成后才拼装”的方式串行等待。创建 run 后立即启动已满足依赖的任务；以下是并行工作线，不是五条全部无条件同时启动：

1. 主线 A：生成 `timeline.json` 和 `media-map.json`。
2. 主线 B：先只生成字幕草稿占位；正式字幕延后到最终音频和全片timeline锁定后一次生成。
3. 主线 C：整理 BGM stem、准备混音命令和片头素材清单。
4. 主线 D：按章节渲染 affine，并对已完成的 I2V 做解码检查。
5. 主线 E：第一章资产齐全后立即拼第一章草稿；随后按章节继续，不等全量。

主线 A 完成一章时间轴即可触发该章的 B、D、E。GPU 任务仍遵守共享 lock，同一时刻只运行一个 GPU 推理/修复任务；GPU 运行期间必须让 CPU、磁盘和图片接口任务继续工作。每条后台命令写入独立日志并记录 PID，不能只在当前终端前台等待。

每30分钟记录一次 GPU 利用率/显存、CPU 利用率、磁盘读写和运行任务。如果 GPU 空闲且存在未启动的独立 GPU 批次，立即启动；如果 GPU 被占用但 CPU 低负载，继续字幕、混音、affine 或章节 QA。只有无可并行工作时才等待。

CPU重任务初始同时运行2个worker，每个FFmpeg限制线程，避免默认各占满全部核心。观察首批5分钟：资源有余量且吞吐上升时增加到3–4个；内存、磁盘饱和或单任务明显变慢时降低。轻量文件检查可穿插。GPU利用率统计看计算引擎/NVIDIA指标，不能只看任务管理器默认3D曲线；NVENC编码也占GPU资源，推理期间须评估显存和吞吐再启用。资源低但没有ready任务时记录依赖原因，不为提高占用率重复生成素材。

### 时间轴最小字段

- utterances：`id`、处理后音频绝对路径、`start_sample`、`end_sample`、采样率；顺序取锁定口播清单，不按目录字符串随意排序。manifest中的`src`是raw来源，不是处理后WAV路径，不得再次执行atempo。
- shots：`id`、`paragraph_id`、关联`utterance_ids`、`start_frame`、`end_frame`（30fps）、`shot_class`、`combo`、`source_path`、`in_frame`、`out_frame`、目标时长、实际覆盖时长、分类变更原因。
- paragraph：按SHOT_PLAN的`anchor.paragraph_interval_share`分配段落音频区间；先累计音频样本，再统一换算视频帧，避免每段单独四舍五入导致漂移。
- 音频主线不因视觉叠化变短；转场使用素材handles或固定时间槽内处理。总视频长度与主音轨差控制在一帧量级；重复utterance引用只关联镜头，不重复播放旁白。
- timeline和media-map在同一个run目录保存版本；新增本集脚本可放`scripts/`，不修改共享管线。

## 不要做

- 不要重新提交已经完成的 90 条 I2V 或176张静帧。
- 不要拉伸、倒放或反复循环五秒 I2V 来填充时长。
- 白名单允许一次符合叙事的首尾叠化循环，旧交接的全面禁循环条款失效；本集未锁定循环的镜头仍默认不循环。
- 不要把一个镜头混成第三类；`image_to_video` 与 `image_camera_motion` 保持分离。
- 不要等待所有 I2V 人工确认才开始章节拼装。
- 不要修改地磁项目、共享规则或已锁定的音频参数。
- 不要因为单个镜头问题暂停所有独立章节。

## 中断恢复

每个阶段结束更新 `CHECKPOINT.json`：

```json
{
  "stage": "timeline|media_map|chapter_assembly|audio_subtitles|intro|delivery|qa",
  "completed": [],
  "running": [],
  "next_action": "下一条可直接执行的动作",
  "blocked": "没有则为空",
  "updated_at": "ISO-8601"
}
```

发生中断时，先读取 checkpoint、manifest 和实际文件，核对进程后从未完成项继续。不要用当前聊天记录猜测状态，不要重复生成已经落盘的可用文件。普通阶段完成后直接进入下一阶段。

## 报告要求

每阶段完成后在 run 目录写日志，包含命令、退出码、实际耗时和输出路径。最终报告必须列出：

- timeline 和 media-map 路径；
- 各章节草稿路径；
- clean/sub 成片路径；
- 自动 QA 结果；
- 仍为 `pending_review` 的镜头；
- 回退到 affine 的镜头及原因；
- 实际采用动态的镜数、原生动态播放秒数及占比；不能拿候选数量代替；
- 未完成事项和下一步动作。

遇到普通脚本错误、路径错误或编码问题，自行修复并继续。只有凭据缺失、外部服务不可用且没有可并行工作时才报告阻塞。
