# Grok交接：《你是一只章鱼》全量生产

项目根：E:/program/1project/video/projects/助眠解说/episodes/you-are-an-octopus。

Codex已补齐锁定口播、事实边界、音轨方案与全量逐镜提示词。当前只有文本计划，无本集配音、图片、真实视频或成片。用户手动将本文件交给Grok执行；收到执行指令后连续完成本集，不在普通阶段结束时等用户催促。不自动发布，不擅改文稿或另选音乐。

依次读story/NARRATION_MASTER.md、story/FACT_NOTES.md、audio/AUDIO_LOCK.md、visual/PRODUCTION_PLAN.md、visual/SHOT_PLAN.json、visual/ALL_SHOT_PROMPTS.md；共享规则为rules/助眠解说/{production-scheduling,execution-continuity,intro-node,visual-motion,subtitles,covers}.md及rules/shared/memory/sleep-aid-visual-style.md。正文锁定；分钟数唯一自动回填。现有章鱼能力是概述，不增加未经核实的纪录、年代或“八个独立大脑”。

## 执行与不中断

创建runs/<批次>/，最小checkpoint记录阶段、已完成、在跑PID/请求ID/日志、下一具体动作、阻塞原因。每阶段结束直接推进；技术错误自主修复，等待外部/GPU时继续依赖就绪工作。续跑先核对文件与进程，不重复提交运行任务，不重做合格素材。检查点不是停止条件。不声称一句“后台继续”即可跨会话推进全部阶段。

GPU遵守shared/gpu-queue/README.md；申请granted并持有任务独占锁才运行TTS、门禁、I2V、VSR。地磁单次免排队不适用于本集，不删除他人锁。允许图片API、CPU字幕对齐、音轨处理、affine和章节拼装并行；CPU重任务先2worker，按实测调3–4个并限制ffmpeg线程，每30分钟查ready任务与实际吞吐。NVENC与GPU计算存在竞争，不盲目叠加。目标锁定后生产≤24小时，不承诺未经实测的耗时。

## 直接开工顺序

1. 文本预检：python prepare_handoff.py。预期280段落、281配音段（1分钟数占位）、190正文镜头、8片头图、83动态候选。此脚本只重建静态计划；正式执行后不可覆盖运行manifest。计划有改动时先备份，manifest放runs。
2. 按章运行audio/jobs/*.json，Python与参数见AUDIO_LOCK。gen_shots.py不自动跳过已有WAV，重启只用第二参数传缺失id，不重新跑整章覆盖音轨。保留raw，处理一次0.7304，门禁沿登记b2。正文一章完成立即建实际时间轴、启动CPU字幕对齐/混音，不等全量。
3. 图片API按SHOT_PLAN逐章全量新做。2×2每格独立16:9，切分保存尺寸/prompt/path/QA；复杂特写single。图片已准备的一章即可开展动态与CPU运镜。长期对话只收路径、清单、文字结论，不重复加载所有高清图。
4. 用实际音轨对齐beat，按PRODUCTION_PLAN已锁的V3/P1覆盖算法生成最终镜头时间表；需要新视角的补图数量先由算法写入manifest。禁止执行时重新挑比例、慢放、逆放或无限循环。短beat预定P1不是临时判定叙事，记录候选与实际使用差别。
5. 六个动态试点→按章I2V→所用素材VSR。沿现有共享实现复用技术，所有输出改本集路径。VSR有损raw与模型raw均保留，不写“无损恢复”。先dry-run与3帧smoke，输出目录必须全新；失败保留日志后换run-id修复，不无限重跑整批。裁切匹配16:9，不能拉伸。明显异常保留标记，正式整镜P1回退；偶发软帧不增加门禁。
6. 正文锁定音轨完成后运行prepare_handoff.py --body-seconds <真实秒> --intro-seconds <估计秒>，生成片头分钟句；生成后实测核对整分钟，只回填该句。采用八张新图与op4四格展开结构，片头纯口播，故事由来开始BGM。参考旧intro脚本只读适配，不覆盖地磁。此轮保持现有正文，不为凑45–55分钟扩稿或拉长静音。
7. 代表章节先拼装验证，其他章节缓存独立渲染、局部返修；统一实际timeline驱动字幕、音轨、画面。输出1080p30fps SAR1，CRF16–18参考、AAC256k，clean和sub两版。字幕Source Han Sans SC Heavy96等沿共享规则，fontsdir不临时替换字体。再做横竖封面，标题占主导，正文一直横屏。

## 完成定义

delivery/你是一只章鱼_1080p_clean.mp4、你是一只章鱼_1080p_sub.mp4；纯旁白/BGM/混音stem；SRT/ASS、字体许可；横竖封面、标题/标签/简介；全量资产manifest、实际时间轴、耗时费用、动态使用与回退清单、QA报告。

检查锁定稿无漏配与重复引入、片头分钟数、完整解码、分辨率帧率、音画时长、章界与首尾抽听、字幕安全区；不要求再加逐帧检测。实际未播放的不能记为看过，自动检查通过不能记为用户验收。自动完成标produced/pending_review区分；问题镜头保留且说明。交付整集，不仅给若干预览。普通检查通过继续后续阶段，真实不可解决的凭据/服务阻塞才报告。

上一集技术参考：projects/助眠解说/episodes/you-are-a-cockroach/HANDOFF_GROK_时间轴与成片优化执行_20261010.md。仅复用工具、调度与经验，不复用图、口播和时间轴。最终回报成片、封面、报告路径和必要争议项即可。
