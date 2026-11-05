# 项目级持久规则（索引）

> 2026-11-06 改为索引：本文件只保留跨线路的“口径与去向”，具体规则在各真源，不在此重复。
> 摘要原文备份：`shared/archive/rules-premerge-20261106/rules/shared/memory/project-rules.md`。

## 目录与入口

工作区根目录只允许 `projects/ assets/ rules/ indexes/ shared/ todos/ README.md`；新增线路同步 `indexes/LINE_INDEX.md`。真源：`indexes/DIRECTORY_STRUCTURE.md`、`document-organization.md`。

## 成本评估

只算本机占用时间（wall-clock/CPU/GPU）与 token；不算人工、人日、工时。口径与算例：`rules/shared/cost-evaluation.md`。

## GPU 统一调度

由管理聊天统一排队，请求写入 `shared/gpu-queue/requests/`，单卡串行，遵守 GPU 锁。协议、状态机、轮询与暂停规则：`shared/gpu-queue/README.md`。

## 静帧运镜

推拉平移默认 affine，幅度可感知、连续、柔和起停、保护主体。参数与边界：`shared/camera-motion/MOTION_GUIDELINES.md`。

## 静态生图与文画匹配

默认独立 GPT 图片 API；关键旁白事实必须可见，不以氛围替代实验/变化/因果。流程与门禁：`video-workflow.md` §2.C；网格细则：`image-grid-generation.md`。

两条跨线路口径保留在此（真源未覆盖）：

- 共享视觉生产默认高清图片配 affine 推拉；真实图生视频只用于低细节、自然内部运动明显且确有必要的少量镜头，**目标约占 20–30%，不是硬性配额**；不得为凑比例牺牲清晰度或事实准确性，争议或清晰度下降时正式版回退 affine。
- 助眠的长期生图视觉方向见 `rules/助眠解说/visual.md`，仅适用于助眠线路。

## 网格与超分

四格用于 1080p 常规环境、九格用于选景/远景/低细节背景、复杂几何与关键特写优先独立生图；RealESRGAN 用于硬边结构，柔和星云优先 Lanczos；原图/裁剪/优化分别保存不覆盖。完整标准：`image-grid-generation.md`。

## 图生视频

每镜只标一种主要动态方式；只有关键动作需要起止状态图；I2V 失败默认回退静帧推拉，且必须按 `video-workflow.md` §2.D 汇总报备，不得静默。
