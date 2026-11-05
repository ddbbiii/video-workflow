# 单集状态

标题:如果生活有一本使用说明书(编剧3 任务;管线 slug `life-manual`)

| 字段 | 值 |
|---|---|
| episode | life-manual(工作区 `E:\program\1project\video\编剧3\`,用户指定命名,不居 episodes/) |
| planning_state | narration_locked(v1,2026-10-24 用户"ok没有问题,直接开始做,直到这个视频完成") |
| execution_state | **final_delivered_v1**(2026-10-24 当日全管线贯通,待用户验收) |
| active_run | runs/20261024-lm-b01(终报 `REPORT_final.md`) |
| 最终交付 | video/final/ 四件:clean 2387.200s=**39.79min**(无音轨)+ narration.wav 2387.1996s(差<1帧)+ with_narration.mp4 + sub.mp4(烧录字幕,音轨md5同clean) |
| QA | 20 像素门禁 PASS(白0/黑0/差-0.001s);字幕 730 条 169/169 一致零重叠;片头 QA ALL OK;i2v 13/13 帧差≤8.18 |
| API 账 | **45 次**(60-85 带内,0 失败);GPU 全本机(TTS 42min+i2v 136.6min 净生成);队列两请求终态 completed,三锁全净 |
| narration | story/NARRATION_MASTER.md v1 锁定(95 段=片头1+引入6+正文83+尾声5;8220 汉字/9135 含标点;由纯旁白配音稿零改字生成,sha256 793b6a8c…1dd9b6) |
| outline | story/OUTLINE.md v1(空间即章节;四母题:钥匙盘/冰箱/夜雨窗/台灯;真实摄影风) |
| fact_notes | story/FACT_NOTES.md v1(13 口径全部带权威来源;画面零新增数字) |
| shot_plan | visual/SHOT_PLAN.json v1(144 镜:8 single+123 tile+13 i2v;节奏加密两轮 106→132→144 保障复用≤2) |
| stills | image/stills 144/144(45 次 API 含重试,60-85 带内;0 失败 0 警告);stills_16x9 144 |
| audio | 口播 170/170(TTS 42 分钟跑完);正文实测 **2375.0s=39.58min**+片头 12.165s;timeline.json 就绪 |
| intro | runs/20261024-lm-b01/intro/batch-20261024-v1:**12.167s/365f/4卡2句/2背景(c2-s01→brg-s01)**,叠化 5.46-5.91 落句间停顿,QA ALL OK;快钩紧凑变体 |
| pacing | manifests/pacing_plan.json:94 段/252 分段(233 P 已渲,19 i2v 段);复用≤2/零相邻/≤12s(P 尾补≤16.5s) |
| audio_plan | runs/20261024-lm-b01/scripts/AUDIO_PLAN.py(b2-warm-male 轻语气,newton→siffre→mariana→本集 连续第4期;atempo 0.774224;BGM -10dB 不默认混) |
| updated | 2026-10-24 15:30 |

## 授权与门禁(本集局部覆盖,记录留痕)

- **2026-10-24 用户授权"直接开始做,直到这个视频完成"**——全程自主推进,同 mariana 2026-10-19 先例,当日交付。
- 三道人工门禁(E 关键动态镜/G 正文视觉/H-J 片头)以**QA 门禁+抽帧目检**替代,成片后交用户验收;零镜头降级/回退(详见 REPORT_final.md 披露节)。
- 生图 API 预算控制在 60-85 次参考带内(实付 45),批次后已报账;未遇 403。
- GPU 沿用助眠解说自管授权(2026-10-07)+三处锁协议;队列请求留痕,终态 completed。

## 待用户

1. 验收四件成片(重点:片头 12.2s 节奏;ch08 抽屉段字幕;尾声调暗收束)
2. BGM 混音(未委托,16 号脚本就绪未运行)
3. 平台封面自制(片头无标题卡,沿 siffre v5 先例)
4. 终版确认后登记 douyin成品.md

## 时长预算

- 旁白 8220 汉字 ÷(215–230 字/分)→ 35.7–38.2 min;加章间留白+片尾 → **成片估 37–40 min**(30+ 线规内,无需扩写)
- 片头:快钩·紧凑变体,锁定稿片头第 1 段(51 字,估 13–15s);无分钟数回填需求(无"接下来的 N 分钟"句)

## 管线(自 mariana 20261019-mdb-b01 移植,25 脚本已适配本集路径)

01 解析 → 05/06 TTS(VoxCPM2 本地,锁协议)→ 08/09 VO+时间轴 → SHOT_PLAN → 07 静帧(远程 API)→ 11 16:9 → i2v(LTX-2.3,GPU 队列)→ build_pacing(v2 节奏:≤12s 换镜/0.4s 叠化/复用≤2 不相邻)→ 15 装配 → 13/14/19 片头(v4.4 工艺)→ 18 重拼 → 22 字幕(FunASR 混合对齐)→ 20 QA → 交付

## 已知坑位清单(承 mariana,全部规避)

①中文 Windows subprocess 一律字节级 pid 检查;15/18 输出目录预建。②口播稿全半角逗号混排,切卡正则须两者兼容。③片头交叉淡化边界±SWAP/2 双向重叠。④生图 CDN 签名含"/"时重存换签名再分析。⑤i2v 批量幂等可续,分块 ≤4 镜防外部中断。⑥camera_motion 不接受非空输出目录(用临时目录)。

## 成片位置（2026-11-06）

成片已统一移至 `shared/delivery/finals/`，本文件内旧的 `video/final/` 路径仅作历史记录。

