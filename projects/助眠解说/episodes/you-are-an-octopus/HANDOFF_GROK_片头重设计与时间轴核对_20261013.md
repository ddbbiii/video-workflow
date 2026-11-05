# Grok 交接：《你是一只章鱼》片头重设计与合成核对

> 片头文案已更新：执行同目录 `HANDOFF_GROK_沉浸式片头文案与镜头_20261013.md`，替换本文第 3 节旧科普提问式文案。本文时间轴核验、配音、交付及回滚要求继续生效。

日期：2026-10-13。用户要求：切片已经做好，优先复用；重新设计片头，改善拼装，并核对播放速度是否与时间轴匹配。本文件是本次返修入口，覆盖旧交接中的片头、配音改速、混音、字幕和 GPU 排队要求。此文档编制阶段未启动视频生产。

## 1. 范围与节点

不从零重做全量图片、I2V 或正文配音。按三个节点推进即可：现有资产与时间轴核验 → 新片头 → 全片拼装及 QA。每节点保存 manifest 和结果，失败只回滚对应节点；保留旧资产，新产物放新 run，禁止覆盖源文件。不另做 60–90 秒样片流程。

项目根：`E:/program/1project/video/projects/助眠解说/episodes/you-are-an-octopus/`

源 run：`E:/program/1project/video/projects/助眠解说/episodes/you-are-an-octopus/runs/20261010-octopus-b01/`

建议新 run：`E:/program/1project/video/projects/助眠解说/episodes/you-are-an-octopus/runs/20261013-intro-reassembly/`，已有同名批次时新建后缀，不覆盖。

## 2. 输入与已做核验

以下路径均在上述源 run 下：

| 输入 | 相对源 run 的路径 | 用途 |
| --- | --- | --- |
| 旧整片 | `delivery/full_video.mp4` | 对照，不沿用旧片头 |
| 正文视频 | `delivery/body_video.mp4` | 正文母片与合成对照 |
| 正文配音 | `audio/narration-dry.wav` | 默认保留的纯旁白 |
| 旧片头 | `intro/intro_video.mp4`、`intro/intro_narration.wav` | 旧版对照，重新设计 |
| 时间轴 | `timeline.json` | 实测语音与正文切点基准 |
| 素材映射 | `media-map.json` | 查源素材及镜头对应 |
| 镜头清单 | `media/shot_clips_manifest.json` | 查现成切片、fallback 与状态 |
| 章节清单 | `chapters/chapters_manifest.json` | 查章节拼装 |
| 旧合成列表 | `delivery/body_concat.txt`、`delivery/full_concat.txt` | 核对顺序 |

脚本和镜头计划入口：

- `E:/program/1project/video/projects/助眠解说/episodes/you-are-an-octopus/story/NARRATION_MASTER.md`
- `E:/program/1project/video/projects/助眠解说/episodes/you-are-an-octopus/visual/SHOT_PLAN.json`
- `E:/program/1project/video/projects/助眠解说/episodes/you-are-an-octopus/visual/ALL_SHOT_PROMPTS.md`

2026-10-13 ffprobe 容器/流信息核验：旧片头 1920×1080、30fps、34.900000 秒；正文视频无音轨，1920×1080、30fps、2602.333333 秒；正文 WAV 48kHz、2602.341813 秒。正文两者差约 0.00848 秒，处于一帧以内。这里只核对媒体信息，未完成全片观感及逐镜速度验收，不能据此宣布没有局部漂移。

时间轴记录正文音频 2602.339 秒、视频 78070 帧/30fps；与实测微小差异需在报告说明。配音 manifest 总长 2495.57 秒不含相同范围的全部留白，不能直接把该差值判为改速错误。

## 3. 新片头如何改

采用已批准的纯视频背景与整句大字片头，取消本集旧版约 34.9 秒的八张静帧结构。时长按主题及实际配音决定，没有硬性秒数；此前 16.6 秒样片获认可，但用户认为略长，应减少重复描述，不能硬剪语音或变速凑时长。

文案采用用户认可的“先进入海底处境，再揭示章鱼身份”版本，详见同目录 `HANDOFF_GROK_沉浸式片头文案与镜头_20261013.md`。旧“如果你是一只章鱼，八条腕足会怎样感知海底？”提案已替换，不再生成。

N 用最终片头＋正文实测总长确定，旧版约 44 分钟仅供估算。正文开头为“不过，今天的你，并不是故事最初的模样”，因此片头落点应指向今天的章鱼，再自然进入远古亲族；不要在片头重复整段进化说明，不沿用其他主题的地磁文案。

- 背景只用视频，从本集正文已验收视频池随机选取。AI 图生视频与图片推拉视频均可；记录候选池、seed、素材 ID、绝对路径和入出点。随机后检查主题、构图和画质，不混入失败版、待验收版、带字幕版或旧片头。
- 保留源视频自身运动，不追加背景数字缩放。不为凑长度慢放、逆放；优先另选足够长的现成片段，必要时换镜。
- 一句一个居中粗体大字卡，整句固定、不滚动。文字由独立透明图层渲染，不与视频一起生成；视频层与文字层分别控制。
- 淡入、淡出各约 1 秒，完全显现时间大于 1 秒。短句优先保证阅读，必要时缩短两端动画。文字参考 96%→102% 缓慢放大，不能造成栅格字号跳动、位置抖动或超出安全区。
- 内部预览参考 1920×1080、60fps。24/30fps 背景转换到 60fps 不等于原生高帧率运动；不默认启用 RIFE，不将重复帧说成新运动。最终正文若保留 30fps，需分别评估片头转到 30fps的文字效果和整片60fps的存储成本，记录最终选择，不能混时基直接拼接。
- 不默认加 BGM、冲击音效或口型。检查章鱼形态、腕足与背景连续性，避免结构融化、突然变速、黑闪或生硬过渡。

参考规则：`E:/program/1project/video/rules/助眠解说/intro-node.md`

批准参考视频：`E:/program/1project/video/projects/助眠解说/episodes/post-tests/sentence-intro-v1/voice-preview/intro-with-voice-preview.mp4`

## 4. 配音：新片头用新配置，正文默认保持原样

新片头采用已批准的轻语气、略有情感声线，再按获批版本提高 1.06 倍速；不能加回此前过强情绪。执行参数读取：

- `E:/program/1project/video/rules/助眠解说/audio-pace.md`
- `E:/program/1project/video/shared/runtime/engines/tts/voice-assets/b2-warm-male/light-expression-profile.json`

关键参数：VoxCPM2，seed 7，CFG 2.0，10 steps，desc_in_text=false，optimize=False，load_denoiser=False。固定音色参考 `E:/program/1project/video/shared/runtime/engines/tts/refs/b2-warm-male_ref.wav`；轻语气 prompt 和逐字稿从配置加载。原始有声段目标 atempo=0.774224；已按0.7304处理的版本只额外加速一次1.06；已按新配置处理的版本禁止再加速。

现有正文配音及时间轴默认不动。若正文也需换声或改速，必须明确另立返修范围，重建正文语音时间轴与镜头时长，不能只压缩音轨或按一个比例推算所有切点。新片头按自身实测配音排镜，接入后正文整体偏移新片头的实际时长。

GPU 队列已由用户暂时废弃，本任务本地检查资源后直接执行，不等待旧队列 grant。字幕生成和配音/BGM混音由用户手动完成，不自动烧录或混入背景音乐。

## 5. 必须核对旧 Grok 切片的速度与时间轴

用户提出的是疑似问题，先查证再改，不全量强行统一速度。总长一致仍可能存在镜头局部错位，需检查全部切片和章节累计边界：

1. 对照镜头计划、media-map、timeline 与实际文件，核对缺失、重复、顺序、源素材和起止点。复用旧素材前核对实际可解码性，不只信 manifest。
2. 用 ffprobe 获取实际 duration、start_time、avg_frame_rate、r_frame_rate、time_base；必要时 count_frames 获取解码帧数并检查 PTS。VFR 不只用帧数÷标称fps推算时长。
3. 检查生成/合成命令中的输入 `-r`、输出 `-r`、fps、setpts、trim、tpad、loop、atempo。源24fps不能被按30fps重新解释播放；帧率转换须保留源时间戳与原始动作时长，输出CFR时记录重复/丢帧方式。裁剪后正确归零时间戳，检查拼接接缝。
4. 每镜对账记录：shot_id、源绝对路径、源入出点、实际速度因子、循环/尾帧及秒数、计划起止/时长、输出实测时长/帧数、单镜偏差与累计偏差。正片图生视频保持原速；有误时按源重新拼装，只返修受影响镜头。
5. 短素材不能偷偷降速填满旁白。有限循环和自身稳定尾帧延长依 `E:/program/1project/video/rules/助眠解说/visual-motion.md`，一次性行为不循环，尾帧延长不算原生模型动态。无法合理补足时明确列出缺口再处理。
6. 核对每章首尾、段落/句子转换、片头→正文边界及全片尾部。实验、变化与因果必须有可见事实对应，不能只靠氛围。检查局部配音和画面偏移，避免“总长对齐、内容错位”。
7. 转场重叠时间必须计入时间轴，不能每镜少几帧导致全片累计缩短。最终无声视频与纯配音时长差不超过一个输出帧；只在不截断语音的前提下用少量尾部静音/末帧舍入对齐，不能用尾部补齐掩盖中间漂移。

保存 `timing-audit.json` 与简短 `QA.md`，列出已证实问题、修复镜头、剩余风险、实测时长和检查范围。不要把未完整播放写成观感已验收。

## 6. 输出与回滚

新 run 下分 `audit/`、`intro/`、`assembly/`、`delivery/` 即可。片头带声大字预览、透明文字资产及句子时间记录留在 `intro/`；对账、concat、manifest 与 QA 留在工作目录。

最终 `delivery/` 只放两个文件：

- `full_video.mp4`：新片头＋正文，完整无声音、无字幕；不烧录片头大字。视频需确实没有音频流。
- `narration.wav`：新片头旁白＋原正文纯旁白，无 BGM，和视频等长。

片头大字保留为单独设计预览，供用户后期使用，不自动改变“最终无字幕视频”交付约束。除用户另行要求，不生成混音最终版、字幕最终版或更多 delivery 文件。

验收：两个文件完整解码；音画等长；无遗漏/重复段落；新片头淡入淡出与语音边界正确；章节累计时间对齐；无异常加减速、明显卡顿、黑闪及文字抖动。确认质量后才将新 run 标为当前交付，旧 run 留作回滚。
