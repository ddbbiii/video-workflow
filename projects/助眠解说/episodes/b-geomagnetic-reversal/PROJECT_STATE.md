# 《地球的磁场会翻转》（b-geomagnetic-reversal）项目记录

当前状态：**completed（2026-10-08 用户确认完结）**。归档与正式产物索引见 `ARCHIVE.md`；以下为历史记录，不代表当前待执行任务。

> 本文件 2026-10-07 新建（此前项目目录下无 PROJECT_STATE.md / RUN_LOG.md）。后续记录只追加，不覆盖。

## 2026-10-07 本集流程特例（局部覆盖，不改长期规则）

- 老大 2026-10-07 明确：本集**跳过 E 关（关键动态镜头人工审核）和 G 关（正文视觉成片人工审核）**，一路自动做到最终视频。
- 这是本集特例，仅适用于《地球的磁场会翻转》本集；**不修改** `rules/shared/video-workflow.md` 或 `rules/` 下任何长期规则，其他集仍按固定流程三道人工门禁执行。
- 片头 J 关（片头人工审核）是否跳过：**老大未说明**，待确认；在得到明确答复前不得默认跳过。
- 记录依据：video-workflow.md §6“用户针对某一集提出的特殊工作流要求，默认仅作为该项目的局部覆盖，必须写入该项目的 PROJECT_STATE 或运行日志”。

## 2026-10-07 静态图全量重制（v3 提示词）

- 批次目录：`gen_rebuild\runs\20261007-v3-stills-b01\`（grid-manifest.json / PLAN.md / qa.json / SELECTED.md）。
- 老大决定：63 镜按 2x2 四格出图（一次调用 2048x1152，裁成约 1024x576 实际像素格，非 2K 图）；复杂几何、关键特写、明显推近镜头单独出 2048x1152。
- 接口：`https://dklapi.com/v1/images/generations`，模型 `gpt-image-2.5-sunburst`，并发 ≤2；密钥读用户环境变量，不落盘。
- 10:01 UTC+8 老大批准试跑结果并授权全部自动跑、ch1-c06a / ch1-c04 按建议重出。
- 10:02–10:37 UTC+8 全部出图完成：HTTP 请求 48 次（成功 41、上游限流失败 7），63 镜最终 pass 43 / note 20 / redo 0；redo 6 镜均以 r1 解决，未用 r2。
- 最终选用清单：`gen_rebuild\runs\20261007-v3-stills-b01\SELECTED.md`；逐张判定 `qa.json`；联系表 `contact_final_1..4.jpg`。
- 未做 AI 超分（RealESRGAN 仅登记候选）；未动 GPU 锁/队列；未改口播、配音、时间线；未改 rules/ 与管线代码；旧图未覆盖、未删除。


## 2026-10-07 动态阶段（v3 静帧 → 每镜动态片段；未拼接）

- 批次目录：`gen_rebuild\runs\20261007-v3-motion-b01\`（MOTION_PLAN.md / motion_plan.json / MOTION_SELECTED.md / final\ / qa\ / logs\ / scripts\）。10:43 开始，11:30 UTC+8 停在 GPU 队列 queued。
- 旧口播时间轴（只读，未重导出、未重建）：`edit\draft_dof_vo_v4\`（inventory.json 63 镜 out_dur，竖版 1188x2112@30，成片 1397.0s）。新 63 镜与旧镜号一一对应，每镜时长取旧 out_dur（30fps 整帧，合计 1421.2s，含 xfade 重叠）。不一致：旧为竖版、本批次横版 1920x1080；拼接时需另定画幅。
- 方法：默认静帧推/拉/平移（camera_motion affine，CPU）；计划 I2V 12/63 镜（ch1-c08、ch2-c07、ch2-c09、ch3-c05、ch3-c07、ch3-c09、ch4-c03、ch5-c06、ch5-c07、ch5-c08、ch6-c01、ch6-c08），引擎 LTX 2.3（自然现象/旧生产 LTX 路由）。
- 伪文字：10 镜轻模糊（inputs_clean\），其中 ch3-c04、ch6-c02、ch6-c03、ch6-c09 用扩大罗盘带的 v2（inputs_clean_v2\）；未加任何标注层（箭头/文字/地图待老大定）。
- 推拉渲染：63 镜 affine\all_v1（CPU，约 10 分钟）+ 4 镜 affine\cleanv2_v1；帧数/尺寸/首中尾帧 QA 全部通过。
- GPU 队列：10:59:30 提交 `zhumian-geomag-v3-esrgan-stills-20261007`、`zhumian-geomag-v3-i2v-ltx-20261007`、`zhumian-geomag-v3-vsr-i2v-20261007`（shared\gpu-queue\requests\），截至 11:30 仍为 queued（STATE.md 自 09:15 未更新；`zhumian-vsr-baseline-c04-streaming-retry4-20261007` 仍标 running 但 PID34164 已不存在）。本执行方无法通知管理会话，未运行任何 GPU 任务、未碰锁。
- final\：63 镜暂定版（全部推拉；计划 I2V 的 12 镜和 RealESRGAN 候选 15 镜暂用原图推拉），清单 MOTION_SELECTED.md。队列放行完成后另出 final_r2\，不覆盖本版。
- 未拼接、未补帧；未改口播/配音/时间线/rules/管线代码；未删除、未覆盖任何旧产物。

## 2026-10-07 GPU 代管 + 动态完成 + 正文拼接（final_r1）

- 授权：老大 2026-10-07 17:55（UTC+11，即 14:55 UTC+8）“全程由你自己处理，就不要问别人”，GPU 队列由本线路代管。
- 队列：zhumian-vsr-baseline-c04-streaming-retry4-20261007 标 failed（PID34164 消失、两处锁无、raw mp4 缺 moov 半截文件原样保留），STATE.md 已备份并更新。本线路 3 个请求依次自授 granted 并 completed：ESRGAN 静帧 15 张（14:57）、LTX 2.3 I2V 12 镜（14:58–15:59）、VSR（16:00–16:55）。
- VSR：c04 单镜用原版 shared\video-restoration\run_vsr_streaming.py 第 1 次即通过（vsr\c04-validate-01，554s，qa_status=pending_review，无硬失败/预警）；未改共享脚本。随后 7 段 I2V 全部 exit 0。早先 retry4 失败原因判断为进程被外部终止（日志无异常、raw 未闭合），非脚本缺陷。
- I2V 抽帧 QA（gen_rebuild\runs\20261007-v3-motion-b01\qa\i2v_qa.json）：通过 7 镜 ch1-c08、ch2-c07、ch3-c07(note)、ch5-c06、ch5-c08(note)、ch6-c01、ch6-c08；退回推拉 5 镜 ch2-c09（熔岩裂隙变形）、ch3-c05（镜头移动）、ch3-c09（手部消失）、ch4-c03（推镜）、ch5-c07（机位移动+器物重排）。
- final_r2\：63 镜（7 镜 I2V+VSR+循环+轻推近；15 镜 RealESRGAN 后推拉；其余推拉），清单 MOTION_SELECTED_final_r2.md；final\ 暂定版保留未改。
- 正文：edit\geomag_v3_final_r1\geomag_v3_body_r1.mp4，1920x1080@30，41910 帧 = 1397.000s（与 v4 一致）。镜头顺序/帧数/叠化（镜间 0.4s、章间 0.5s）按 draft_dof_vo_v4 复原；音轨为 v4 原口播混音直接拷贝（与 v4 逐字节一致），未重配音。时间轴 geomag_v3_body_r1_timeline.json，QA FILM_QA.json：时长一致、音轨一致、blackdetect 0 段、解码无错。
- 字幕：v4 无字幕，未加。BGM：v4 无单独 BGM 层，沿用 v4 混音原样，未另加。片头：本次未做，待定（J 关仍未说明）。未加文字/箭头/地图标注。
- 预览：C:\Users\10060\geomag_v3_final_r1_preview_960x540.mp4（118MB）与 _small 版（78MB，已拷盒子）。
- 未删除/覆盖任何旧产物；未改 rules\、口播、配音。

## 2026-10-07 22:42–23:05 (UTC+8) 带字幕版 geomag_v3_final_r1_sub
- 依据：rules\shared\audio\voice-and-subtitles.md、video-workflow.md（2026-10-07 22:32 版），样式 B。
- 文本：script_v4_ch1.md 与 script_v4_ch2-6.md 的口播全文，逐字照用，只做断行。
- 时间：本机 FunASR（seaco paraformer large + fsmn vad，CPU），对正片音轨做字级时间戳，未使用 GPU；音轨 SHA256=4D2736456E3474D860B0660321A5CDFE4F00E90085838FCD232ACB4641513AF5。
- 字幕：422 条，单行最多 22 字；Microsoft YaHei 48px，暖白字，约 40% 黑色半透明直角底条，MarginV 86（约 8%）。
- 产物（均在 edit\geomag_v3_final_r1_sub\）：
  - geomag_v3_body_r1-subtitles.srt / .ass
  - geomag_v3_body_r1-burned-subtitles.mp4（1397.000s，41910 帧，音轨与正片一致）
  - SUB_QA.json、SUB_QA_REVIEW.md、qa 联系表、scripts\、work\
- 干净母版仍为 edit\geomag_v3_final_r1\geomag_v3_body_r1.mp4，未改动。
- 待办：开场节点（intro-node.md）尚未制作，按 workflow 字幕应在 intro/J 门之后，本版为正片字幕预览，片头接入后需整体平移或重出。

## 2026-10-07 23:20 (UTC+8) 字幕样式 r2 试样（前 10 秒）
- 老大反馈：字体加大（抖音），黑底条变浅一半。
- edit\geomag_v3_final_r1_sub\style_r2\：
  - geomag_v3_body_r1-subtitles-style_r2.ass：字号 48→56，底条 &H99101010（约40%不透明）→&HCC101010（约20%）；位置、颜色、断行、时间不变。
  - geomag_v3_sub_style_r2_first10s.mp4：干净母片前 10s 烧录，1920x1080，带原音轨（AAC 192k）。
  - geomag_v3_sub_style_r2_compare.jpg：2.2s / 5.5s / 7.6s 新旧对比。
- 安全区检查：全片 422 行在 56px 下最宽约 1428px（含底条），没有超出 90% 宽度安全区。
- 原 ass、srt 和烧录版未改。

## 2026-10-07 23:25 (UTC+8) 字幕样式 r3 试样（前 10 秒）
- 老大反馈：字再大三号。
- 本轮以 style_r2 为基础，只把字号 56 改成 59；底条仍为 &HCC101010（约 20%），位置、颜色、断行、时间不变。
- 产物在 edit\geomag_v3_final_r1_sub\style_r3\：
  - geomag_v3_body_r1-subtitles-style_r3.ass
  - geomag_v3_sub_style_r3_first10s.mp4（1920x1080，10s，带原音轨）
  - geomag_v3_sub_style_r3_compare.jpg（r2/r3 底部原尺寸裁切对比）
- 安全区检查：59 号下全片 422 行最宽约 1503px（含底条），没有超出 1680px 的左右边距或 90% 宽度。
- 已有文件未改动。

## 2026-10-07 23:35 (UTC+8) 字幕样式 r4 试样（前 10 秒，抖音大字幕）
- 参考：老大提供的抖音截图。
- 字体：思源黑体 SC Heavy（SourceHanSansSC-Heavy.otf，v2.005R，SIL OFL 1.1）。
  - 来源：Adobe 官方 GitHub release 09_SourceHanSansSC.zip。
  - 放在 style_r4\fonts\，用 fontsdir 引用，未装入系统；SHA256 6374B11B…A985E。
- 样式参数：
  - 字号 96（libass 实际字面约 66px）。
  - 白字 &H00FFFFFF，黑描边 5px，阴影 2px（&H80000000），无底条。
  - 底部居中，左右边距 96，MarginV 118；字幕中心约在画面高度 85%。
- 文字、时间、断行不变。
- 安全区检查：422 条中最宽 1660px（22 字的两行），没有超出 90%（1728px）。
  - 方案一：改成每行最多 16 字，需要重新断行 150 条（暂未执行）。
  - 方案二：超宽行单独缩小字号，需要处理 0 条。
- 产物在 edit\geomag_v3_final_r1_sub\style_r4\：
  - ass、first10s.mp4
  - compare.jpg、2 张 1080p 帧
  - douyin_reference.png
- 已有文件未改动。

## 2026-10-07 23:45–00:05 (UTC+8) 片头试点 pilot-grok-op4（仿「县城葱姜蒜」，只用 CPU）
- 老大批准按 PLAN_本地仿制片头.md 做试点，后来更正为约 12 秒。
- 目录：intro\pilot-grok-op4\。未改 rules、共享模板和已登记的脚本，未用 GPU 或 LTX，未动口播和音频。
- 视频：
  - op4_L_12s.mp4：温和版，12s，360 帧，1080p30，含合成音效。
  - op4_H_12s_violates-intro-rules_compare-only.mp4：**违反现行 intro-node.md 禁止项（故障闪烁、冲击音），仅供对比，不得接入成片**。
  - 4 秒初版 op4_L.mp4 和 op4_H_violates-intro-rules_compare-only.mp4 一并保留。
- 素材：均为 v3 stills（gen_rebuild\runs\20261007-v3-stills-b01\raw）。
  - 分格 1：ch1-c10 / ch2-c02 / ch4-c08 / ch6-c06；主视觉 ch1-c04_r1。
  - 分格 2：ch1-c12 / ch2-c09 / ch5-c05_r1 / ch6-c09。
  - 蒙太奇：ch4-c06 / ch3-c08 / ch5-c09 / ch1-c13_r1；末镜 ch4-c04_r1。
  - 11.4s 起接干净母片前 18 帧。
- 标题与音效：
  - 标题“地球的磁场 / 会翻转”，思源黑体 SC Heavy（OFL）；L 白字黑描边，H 红字黑描边。
  - 音效用 numpy 合成（whoosh、hit、chime），没有使用外部素材。
- 脚本：op4_compose.py（4s）、op4_12s.py（12s），都是一次性脚本。
- 产物清单：manifest.json、manifest_12s.json、联系表、三方对比图 op4_compare_ref_L_H_0-4s.jpg。
- 自检：两版都是 12.000s、360 帧、1920x1080，有音轨（L max -4.4dB，H max -1.1dB）。
- 状态：待老大评审，未接入正片。

## 2026-10-08 06:27–06:55 (UTC+8) 片头范例 A（pilot-grok-op4-vo，技术方案用，文案非定稿）
- 目录：intro\pilot-grok-op4-vo\。
- 配音：b2-warm-male，VoxCPM2 seed7 / cfg2 / 10steps，ultimate，参考音 md5 7b7d0ae6…。
  - GPU 请求 zhumian-geomag-intro-op4-vo-tts-20261008：06:31:15–06:32:21 completed。占 shared\work\cache\gpu.lock，跑完即放锁。
  - 后处理：去首尾静音，atempo 0.88。
- vo_gate：在 ddbbi 上运行了 box 的 vo_gate.py（md5 19234d45…，与 box 一致），依赖装在批次 tmp\pylibs 里，没有改共享 venv；profile 用 ch1 b2 质检的 profile_A_scratch.yaml。
  - 结果 3/3 通过（F0 -0.5 / -1.9 / -0.7 半音）。
  - box 本机跑门禁时因内存不足被 OOM 终止。
  - 父会话要求注明：本范例不作为过门禁的依据；文案定稿后的正式配音必须重新过 vo_gate。
- 成片：op4_vo_A.mp4 共 16.58s，其中片头 14.57s，加正片开头 2s；另有 op4_vo_A_clean.mp4（无字幕）。
- 其它产物：narration wav、srt、ass、联系表、manifest、build_op4_vo_A.py。
- 画面：
  - 第 1 句：四格拼贴（ch1-c10 / ch2-c02 / ch2-c09 / ch4-c08）从中心弹出、滑开；ch1-c10 放大铺满后慢推，再叠化到 ch2-c02。
  - 第 2 句：ch3-c08 → ch4-c06 → ch1-c13_r1，0.2s 叠化，2–3% 推拉。
  - 第 3 句：ch4-c04_r1 慢推。
  - 末段：艺术字「地球磁场」，Ma Shan Zheng（SIL OFL 1.1，取自 google/fonts 官方仓库，放在批次 fonts\），宽 1264px，占画面宽度 65.8%，0.6s 淡入。
  - 结尾硬切进正片。
- 字幕 r4，无音效，无 BGM。
- 未能复制到盒子：文件传输工具只允许读取 C:\Users\10060，而本轮要求不往 C 盘放东西。
- C 盘中转（此前已放入，未删除）：C:\Users\10060\op4vo_xfer\，约 1.4MB，内容为 3 条 wav、meta.json 和 kp\（vo_gate 脚本副本）。

## 2026-10-08 07:11–08:05 (UTC+8) 地磁完整版 r1（edit\geomag_v3_full_r1\）
- 依据：
  - intro\script-revision-20261008\HANDOFF_GROK_片头衔接微调.md 和 INTRO_COPY.md（07:08）
  - rules\助眠解说\intro-node.md、background-music.md（10-08 07:06），subtitles.md（10-07 23:47）
  - rules\shared\audio\voice-and-subtitles.md、video-workflow.md、visual\cover-and-intro.md
- 复用：
  - 正片画面 edit\geomag_v3_final_r1\geomag_v3_body_r1.mp4，除 c06b 段外逐帧不变
  - 正片口播
  - r4 字幕时间轴（c07 起整体平移 -2.5667s）
- 新做：
  - 片头三句定稿文案，b2-warm-male seed7/cfg2/10steps，atempo 0.88；画面为四格拼贴、单图和马善政艺术字「地球磁场」；无 BGM。
  - 正文 c06b 改为「我们从六个问题，慢慢走近这个谜。」：1x 速，原位替换，段长 187 帧变 110 帧，affine 重渲染，前后叠化重建。
  - 全片 BGM 混音、字幕。
- vo_gate：在 ddbbi 上运行，用 pilot tmp 里的独立依赖；f0_ref 取 102.7（registry）。4/4 首次通过，偏移分别为 i01 正常、i02 +0.6、i03 +0.4、c06b -1.4 半音。
- 成片：
  - full\geomag_v3_full_r1_clean.mp4（1408.4s，42252 帧）
  - full\geomag_v3_full_r1_subtitled.mp4
  - 响度 -17.1 LUFS / -1.5 dBTP；按老大指示暂不加限幅器，要更响时再改。
- QA 通过，详见 edit\geomag_v3_full_r1\REPORT.md。联系表还需人工目检。
- 遗留：
  - 1151–1250s 四处疑似口播差异未修，全片新时间为 1162.74 / 1195.18 / 1208.52 / 1261.94s，见 REVIEW_TIMEPOINTS.md。
  - C 盘误放了一个临时脚本 C:\Users\10060\AppData\Local\Temp\x.py，未删除。
  - 远程执行工具会自动往 C:\Users\10060 写临时脚本。
  - E 盘文件传不到盒子（工具不允许访问该路径）。
- GPU：TTS 07:23:00–07:23:37；NVENC 07:41:48–07:52:48。两次都占 shared\work\cache\gpu.lock，跑完已释放。
## 2026-10-08 08:45–08:50 (UTC+8) 从 legacy-source 搬迁到 episodes（视频号规划批准）
- 依据：`projects\助眠解说\logs\MIGRATION_legacy-source_20261008_r2.md`，加上规划 08:41 定的子目录映射。
  - 静帧放 image\stills\，动态镜头放 video\clips\，正片画面源放 video\source\。
  - 口播 takes 放 audio\vo-raw\，音轨和字幕放 audio\，剧本放 story\。
  - 成片和交付物放 video\，片头放 video\intro\，封面放 image\covers\，归档放 archive\。
- 结果：同盘 Move-Item 搬了 3068 个文件，共 20.33 GB。搬前搬后逐个比对 md5，全部一致。
- 其他去向：
  - 马善政字体和许可搬到 `assets\助眠解说\intro\fonts\`；b2 的 vo_gate profile 搬到 `assets\助眠解说\voices\b2-warm-male\vo_gate\`。
  - legacy-xfer 和 voices 搬到 `projects\助眠解说\archive\`。
- 跳过 2 个：`geomag_v3_full_r1_subtitled.mp4` 和 `geomag_v3_full_r1_bodyonly_clean.mp4`。当时被 PotPlayer 打开，仍在旧位置 `legacy-source\...\edit\geomag_v3_full_r1\full\`，关闭播放器后要补搬到本集 `video\`。干净母版 `video\geomag_v3_full_r1_clean.mp4` 已经搬好。
- 原地保留在 legacy-source：
  - 废稿 11.51 GB，等规划登记后删，见 `logs\DISCARD_legacy-source_20261008.md`。
  - 与 assets 重复的 13 个文件。
  - 口播检查依赖 1.01 GB，由规划迁到 shared\runtime。
  - GPU 请求记录原件。已复制一份到 `shared\gpu-queue\requests\zhumian-geomag-full-r1-nvenc-20261008.json`。
  - 搬空的旧目录全部保留，没有删除任何文件或目录。
- 执行日志：`projects\助眠解说\logs\MIGRATION_EXEC_20261008.md`。
- 待规划处理：脚本、清单、交接文档和 rules 里写死的 legacy-source 路径都还没改（rules\助眠解说\intro-node.md、covers.md，以及约 57 个脚本和清单）。旧脚本按原路径已经跑不起来。本文件之前各条记录里的路径都是旧位置。

## 2026-10-08 (UTC+8) legacy-source 退役收尾（视频号规划）
- 81 个脚本和配置移到 `shared\workflows\助眠解说\b-geomagnetic-reversal\`，按旧 legacy 的相对结构放。路径已改到本集新位置，还没重跑。说明和未解决的引用见 `shared\workflows\助眠解说\README.md`。
- 口播检查依赖（pylibs、modelscope、kepu-pipeline-box）移到 `shared\runtime\envs\vo-gate\`，run_gate.ps1 已改成指向那里。
- 本集 12 个清单 json、README.md 和 `video\manifest.json` 在原位置改了路径，旧版存为 `.bak-20261008`。manifest 现在 15/17 条能找到文件，剩下 2 条是 PotPlayer 占用的成片。
- 废稿和 13 个与 assets 重复的文件，登记为 LGCY-ZM-001～024 后删除，释放约 11.49 GB。
- 临时目录改到 `shared\work\scratch\zhumian-geomag-full_r1-tmp` 和 `zhumian-geomag-op4_vo_A-tmp`。
- legacy-source 里还剩三个文件：
  - `geomag_v3_full_r1_subtitled.mp4` 和 `geomag_v3_full_r1_bodyonly_clean.mp4`，被 PotPlayer 占用，关掉播放器后补搬到 `video\`。
  - GPU 请求记录原件 `System.Collections.Specialized.OrderedDictionary`。
- 本文件前面各条记录里的路径都是旧位置，作为历史保留，没有改。

## 成片位置（2026-11-06）

成片已统一移至 `shared/delivery/finals/`，本文件内旧的 `video/final/` 路径仅作历史记录。

