# 助眠线双机拆解设计（v0.1）

> **状态：评估完成，暂不实施（2026-11-06）。** 结论见第 11 节：收益 1.15–1.3×，维护成本高于收益，改为单机优化 + 临时手搬。
> 2026-11-06　范围：仅助眠解说　目标：Windows 出画面、Mac 出后期，两台机器并行
> 前置事实：ddbbi 为 Windows + GPU（ComfyUI 8188/8189/8190、voxcpm2 TTS、VSR）；Mac 为 Apple Silicon，SSH(22) 已开，两端均装 Tailscale；`shared/exchange/sync` 为 Syncthing 共享根；`shared/gpu-queue` 已有请求文件协议。

## 1. 为什么这样拆

拆解的依据不是“把活分一半”，而是四条硬约束：

1. **按资源类型拆**：GPU 是单卡独占资源（现有 gpu-queue 就是为此设计的），CPU 是可并行的。所以 TTS/静帧/I2V/VSR 必须串在 Windows；ASR/字幕/编码/QA 是 CPU+IO，天然适合 Mac。
2. **按门禁拆**：E（关键动态）、G（正文成片）、片头三道人工审核是天然断点。审核点之前的东西不能跨机乱飞，审核点之后才适合交接。
3. **按数据契约拆**：每个阶段之间只传「文件 + manifest」，不传进程状态。这样任何一段都能在任一台机器重跑，不会因为机器不同产生分叉。
4. **先迁可独立验收的**：ASR、字幕、QA、编码这几段有明确输入输出和可自动判定的成功标准，先迁风险最低；TTS 和 I2V 依赖 GPU 与固定 seed，不能轻易换机器。

## 2. 拆出来的作业单元

| ID | 作业 | 输入 | 输出 | 执行端 | 依赖 |
|---|---|---|---|---|---|
| W1 | 静帧生成（含网格裁剪） | 事实卡 + 提示词包 | `stills_vN/*.png` + manifest | Windows GPU | 剧本锁定 |
| W2 | 动态镜头（H3/Wan/LTX） | 已批准静帧 | `clips/*.mp4` + 哈希 | Windows GPU | 门禁 E 前 |
| W3 | TTS 逐镜配音 | 旁白 + 声线 + seed | `audio/shot_*.wav` | Windows GPU | 声线确认 |
| M1 | ASR 词级对齐 | 母带 wav + 锁定文本 | `words.json` / `cues.raw.json` | **Mac** | W3 或用户母带 |
| M2 | 字幕 DP 对齐 + ASS/SRT | `cues.raw.json` + 全局偏移 | `body.ass` / `body.srt` / `cues.json` | **Mac** | M1 |
| M3 | 片头渲染 | 三句文案 + TTS + 时间轴 | `intro.mp4` + 状态帧 | **Mac**（ASS+FFmpeg 两层） | 门禁 3 前 |
| M4 | 合成与烧录 | 片头 + 正文 + 字幕 + 音轨 | clean / sub 两版 | **Mac**（VideoToolbox） | 门禁 G 通过 |
| M5 | QA 门禁 | 成片 + 计划时长 | 黑帧/白帧/音视差/帧数报告 | **Mac** | M4 |
| M6 | 联系表与抽帧 | 视频 | contact sheet + 抽帧 | 任一端 | — |
| M7 | 清单与文档校验 | 各阶段 manifest | 一致性报告 | 任一端 | — |

Windows 独占：W1、W2、W3。Mac 独占：M1–M5。其余两端皆可。

## 3. 三套交互方案

### 方案 A：文件队列（Syncthing 搬运 + 双机轮询）

**原理**：把 `shared/exchange/jobs/` 当作邮箱。提交端写 `pending/<jobid>.json`；执行端轮询，用原子改名 `claim` 抢占（`Move-Item` 在同卷上是原子的），执行完写 `done/<jobid>.result.json`。Syncthing 负责把文件复制到对端。没有网络服务，没有端口，没有常驻进程之间的连接。

```json
{
  "id": "20261106-m1-001",
  "stage": "asr-align",
  "inputs": {"master": "episodes/siffre/audio/vo_v2.wav", "text": "episodes/siffre/story/NARRATION.md"},
  "params": {"engine": "funasr", "lang": "zh"},
  "outputs": ["episodes/siffre/audio/words.json"],
  "runner": "mac",
  "created": "2026-11-06T00:30:00+08:00"
}
```

**优点**
- 零新增依赖：Syncthing、目录、JSON 都已在用；断网/关机不丢任务，恢复后自动续。
- 天然幂等：job 文件带输入哈希，重复提交可判重。
- 调试简单：出问题看目录就知道卡在哪一步。
- 与现有 `gpu-queue` 同一套语义，迁移成本最低。

**缺点**
- 延迟：Syncthing 扫描间隔（默认 ~10s）加上两端轮询，一个 job 端到端有 10–60 秒空转。
- 并发控制弱：抢占靠改名，两边时钟/文件锁要小心；不适合秒级交互。
- 大文件同步慢：单集静帧/I2V 十几 GB，首次同步是主要时间成本（后续增量）。

**适用**：批量阶段（ASR、字幕、QA、编码），也就是助眠线 80% 的 CPU 工作。

---

### 方案 B：SSH 远程执行（指令下发 + rsync 回传）

**原理**：Windows 端直接 `ssh mac "cd /Users/.../job && python run.py --in ... --out ..."`，把 Mac 当远程 shell 用。数据用 rsync over Tailscale 推拉，或者继续用 Syncthing 同步、SSH 只负责触发。SSH 免密（密钥）后可无人值守。

**优点**
- 延迟低：秒级启动，适合“跑一段看一眼”的交互式返工。
- 可精确控制：能拿到 stdout/exit code，失败立刻知道原因。
- 不依赖同步延迟，路径可直接映射。
- 天然支持并行：一条 ssh 一个进程，`&` 多个 job。

**缺点**
- 需要维护 SSH 密钥、known_hosts、Mac 的远程登录开关与休眠策略（合盖/睡眠会断）。
- 断线即失败：长任务（40 分钟编码）必须 nohup + 日志轮询，否则连接一断就前功尽弃。
- 路径映射脆弱：两台机器的目录必须严格对应，否则命令写死在脚本里。
- 权限面变大：Mac 暴露 SSH 给局域网/Tailscale。

**适用**：单点返工（改一条字幕立刻重烧）、需要即时反馈的调试。

---

### 方案 C：常驻 Worker + HTTP 队列（工程化）

**原理**：Mac 上跑一个常驻 Python worker（FastAPI/Flask），暴露 `/submit`、`/status`、`/result`；Windows 端 POST 任务。任务状态存 SQLite。传输仍可用 Syncthing 或 HTTP 上传。

**优点**
- 语义最清晰：任务有 ID、状态机、重试、超时、并发度。
- 可观测：一个 `/status` 看全部在跑什么。
- 扩展性好：以后加第三台机器只是多一个 worker。

**缺点**
- 新增一个需要维护的服务（开机自启、崩溃重启、端口、鉴权）。
- 开发和调试成本最高；助眠线当前只有两台机器，收益不明显。
- 服务挂了任务全停，反而不如文件队列皮实。

**适用**：机器数量上去（3 台以上）或需要对外提供能力时。

## 4. 对比

| 维度 | A 文件队列 | B SSH 远程 | C HTTP Worker |
|---|---|---|---|
| 端到端延迟 | 10–60 s | 1–3 s | 1–3 s |
| 新增依赖 | 无 | SSH 密钥、rsync | 常驻服务、端口 |
| 断网/睡眠容忍 | 强（续跑） | 弱（断线即失败） | 中（需重试） |
| 大文件传输 | Syncthing 增量 | rsync 增量 | 需自建 |
| 调试难度 | 低 | 中 | 高 |
| 并发能力 | 弱 | 中 | 强 |
| 与现有体系契合 | 高（同 gpu-queue） | 中 | 低 |
| 一次性搭建量 | 小 | 小 | 大 |

## 5. 推荐：A 为主，B 为辅（混合）

**骨架用 A**：所有阶段作业都走 `jobs/` 文件队列，Syncthing 搬运，两端各跑一个轮询器。理由：复用已有基础设施、断网可续、与 gpu-queue 语义一致、出问题好查。

**热点用 B**：字幕返工、单镜重烧这类“改一下立刻看”的场景，Windows 直接 `ssh mac` 触发，省掉同步空转。B 不承担长任务，只做秒级动作。

**不要现在上 C**：两台机器用不上服务化，等出现第三台或需要对外接口再说。

## 6. 落地顺序

1. **M1 ASR 对齐**先迁：输入输出最干净（wav + 文本 → json），Mac 的 FunASR/whisper.cpp 比 Windows CPU 快，且不碰 GPU。
2. **M2 字幕 DP**：复用 `realign_subtitles.py`，纯 Python + numpy，Mac 直接跑。
3. **M5 QA**：黑帧白帧/音视差用 FFmpeg + PIL，Mac 上跑得快，结果写回报告。
4. **M4 合成/烧录**：VideoToolbox 硬编，最费时的编码环节转移，收益最大。
5. **M3 片头**：ASS + 两层 FFmpeg，Mac 可跑但要带字体文件（BaoCanMouHuiTing 22 MB，走 Syncthing）。
6. W1–W3 永留 Windows，不在拆解范围内。

## 7. 落地时要注意

- **路径映射**：job JSON 里一律写相对 `exchange/` 根的路径，两端各自拼绝对路径，禁止写死 `E:\` 或 `/Users/`。
- **输入指纹**：job 带输入文件 sha256，输出带产物 sha256，重跑可判断是否真的变了。
- **抢占原子性**：`pending/` → `running/` 必须用同卷 rename，不能先读后写。
- **心跳与回收**：worker 每 30 s 写 `heartbeat.json`；超过 3 个周期没心跳，把 `running/` 里的 job 退回 `pending/`。
- **门禁落点**：E/G/片头的人工审核结果写成 `approvals/<episode>.json`（谁、何时、通过哪个 hash），作为后续 job 的准入条件。
- **Mac 睡眠**：跑批时必须 `caffeinate`，否则合盖即中断。

## 8. 修订（2026-11-06）：M4 Pro 48GB 带来的分工变化

### 8.1 硬件底牌

| | ddbbi（Windows） | MacBook Pro |
|---|---|---|
| 芯片 | RTX 5060 Ti | M4 Pro |
| 显存/内存 | 16 GB GDDR7 | 48 GB 统一内存（GPU 可用约 36 GB） |
| 带宽 | 448 GB/s | 273 GB/s |
| 编码器 | NVENC（h264/hevc） | VideoToolbox（h264/hevc/ProRes） |
| 生态 | CUDA，ComfyUI/自定义节点成熟 | MPS，部分算子与节点缺失 |

**结论：算力仍是 Windows 强约 2 倍，但 Mac 的内存容量是 2.25 倍，这是结构性差异，不是速度差异。**

### 8.2 能力分档

**A 档：直接搬，无争议**
ASR 对齐、字幕 DP/ASS、合成、烧录、QA、联系表、文档校验。CPU/ANE 足够，且这些活 Windows 上也在抢 CPU。

**B 档：能跑，但要实测再定**
- ComfyUI 静帧（SDXL/Flux）。SDXL 约 Windows 的一半速度；**Flux fp16 约 23 GB，16 GB 卡要 offload，Mac 能整块放进内存**，这一档 Mac 可能反超。
- voxcpm2 / Qwen3-TTS（MPS）。速度可能只有 CUDA 的 0.4–0.7 倍，且需验证 seed 复现与音色一致性。
- 片头 ASS 两层渲染（纯 CPU，稳）。
- Blender EEVEE（Metal 可用）、ProRes 中间片。

**C 档：不建议**
- H3 / Wan 大模型 I2V：依赖 CUDA 算子，MPS 上易缺 op 或慢到不可用。
- VSR（Real-ESRGAN / BasicVSR++）：自定义 CUDA kernel 多。
- LoRA 训练：Mac 上 sd-scripts 支持差，速度低一个量级。

### 8.3 修正后的分工：按「集」并行，而不是只按「阶段」切

原来的 A 方案只把单集内的阶段切开，收益有限，因为真正的等待发生在门禁（E/G/片头）和 GPU 排队上。48 GB 内存让 Mac 可以**独立吃下一整集的轻量生产**，这才是并行的主收益。

三条通道：

| 通道 | 机器 | 内容 |
|---|---|---|
| 1 生成 | Windows GPU | I2V、TTS、VSR、LoRA、大批量静帧 |
| 2 后期 | Mac CPU/ANE | 对齐、字幕、QA、编码、合成 |
| 3 副产线（新） | Mac GPU | 整集薄管线：API 静帧 + TTS + compose + 片头，适合短集/试验集 |

调度规则不变（文件队列 + gpu-queue 语义），但 job 要加两个字段：

```json
{"capability": "cpu|gpu-cuda|gpu-metal", "prefer": "mac|win|any", "est_sec": 900}
```

调度器按 capability 路由；`prefer=any` 时按当前负载选空闲的一台。

### 8.4 判据：不比谁快，比谁闲着

Mac 接管一段的门槛不是“比 Windows 快”，而是“**Windows 在做别的、Mac 本来闲着**”。只要单件速度不低于 Windows 的 50%，并行总吞吐就是净赚。所以 B 档值得实测，C 档才排除。

### 8.5 落地前必须实测的 5 项

| # | 测什么 | 方法 | 判据 |
|---|---|---|---|
| 1 | 静帧吞吐 | 同 prompt/seed 各出 4 张 SDXL + 4 张 Flux | ≥0.5× 即接管；Flux 看是否反超 |
| 2 | ASR 速度 | 40 分钟母带，whisper large-v3 vs FunASR | 实时因子 <0.1 即合格 |
| 3 | 编码速度/质量 | 同 10 分钟 1080p30，x264 / NVENC / VideoToolbox 对比 | 同码率下体积与观感，慢于 20 fps 不接管 |
| 4 | TTS 一致性 | 同一章、同 seed，CUDA vs MPS 各出 3 镜 | 音色漂移可接受才用 |
| 5 | I2V 可行性 | 1 条 5 秒 H3 片段跑 MPS | 能跑通再谈，跑不通就归 C 档 |

### 8.6 现实约束

- 统一内存默认只给 GPU 约 75%，要更多需 `sudo sysctl iogpu.wired_limit_mb`。
- 持续满载会降频，MacBook Pro 靠风扇，长批任务要留散热余量。
- 合盖即睡，跑批必须 `caffeinate -dimsu`。
- MPS 缺 flash-attn/xformers/sageattention，ComfyUI 的加速节点多数不可用。

## 9. 效率与损耗评估（2026-11-06）

### 9.1 单集机器时间基线（取自项目记录）

| 阶段 | 机器时间 | 依据 |
|---|---:|---|
| i2v 批量（约 40 镜） | 8 h | mariana 记录：siffre i2v running，预计 8 小时，GPU 99% |
| TTS 全片 | 0.7 h | 编剧3：TTS 42 min |
| 编码 clean + sub | 1–2 h（x264）／0.4 h（NVENC） | 2088 s 成片两次编码 |
| ASR + 字幕 + QA | 0.8 h | 本机 CPU |
| 片头渲染 | 0.3 h | ASS 两层 |
| VSR（可选） | 0–3 h | 单镜 554 s |
| **合计** | **约 11–12 h**，其中 GPU 约 72% | |

### 9.2 天花板

GPU 段不可拆，CPU 段可外移。按 Amdahl 定律，上限 = 1 / (1 − 0.72) ≈ **1.39×**。也就是说，拆机最多把吞吐提到 1.4 倍，不会更多。

### 9.3 收益来源与量级

| 来源 | 量级 |
|---|---|
| 把 2–3 h 后期藏进 8 h GPU 窗口 | 单集 wall-clock −20~25% |
| GPU 不再因等 CPU 空转 | 吞吐 +25~35% |
| Mac 分流部分静帧/试验 i2v（B 档） | 再 +5~10%（不确定） |
| 故障容错（一台挂了另一台能顶） | 非吞吐收益 |

### 9.4 交流损耗

| 项 | 量级 |
|---|---|
| 数据搬运 | 每集约 6 GB（静帧 0.4 + i2v 2 + 音频 0.3 + 成片 3）；千兆 1–2 min，WiFi 5–10 min |
| 队列延迟 | 10–60 s/job，每集约 10 个 job → 1–10 min |
| 版本漂移 | 脚本两端不一致导致返工，早期 5–15%，稳定后 2–3% |
| 故障恢复 | Mac 睡眠、同步冲突、半截文件，早期 5–10% |
| 人的注意力 | 两套日志、两处门禁记录 |

综合：稳定期约吃掉 8–15% 的机器时间，前 2–3 集约 20–30%。

### 9.5 净结论

- **稳定期吞吐约 1.15–1.3×**，单集 wall-clock −15~25%。
- 想再多，得动 GPU 段本身：减少 i2v 镜数、改 NVENC、批量静帧，收益比拆机大。
- 真正的瓶颈往往是人工门禁等待；如果一集要等一晚审片，拆机不解决这个问题。

## 10. 附：对 polo小球（土豆阶梯）项目的适用性

**结论：这个项目可移植性最好，但不需要拆机机制。**

- 全栈是 Pymunk（单线程物理）+ Pillow（逐帧合成）+ FFmpeg，零 CUDA，纯 CPU，Mac 直接能跑。
- 但单次渲染自述 40–90 秒，G1 的 sweep 也是秒级；任务太短，队列同步/排队的分钟级开销反而占大头。
- 硬件对比：i7-14700KF（8P+12E，28 线程）单核与 M4 Pro 持平、M4 略优 5–10%；多线程 Windows 反而占优（28 vs 14）。**Mac 不是更快，只是更便携。**
- 正确用法：代码走 git/Syncthing 直传，两端各自本地跑；只有 A/B/C/D/E 配置 sweep 需要并行时才两台一起上。
- 迁移清单：Python 3.12 + pymunk 7.x（确认 arm64 wheel）+ pillow + numpy + ffmpeg(brew)；字体文件要一起带；脚本里的 Windows 绝对路径改相对路径。

## 11. 最终结论（2026-11-06）

**不实施完整拆机。**

| 判据 | 评估 |
|---|---|
| 吞吐收益 | 1.15–1.3×（Amdahl 上限 1.39×，因 GPU 占 72%） |
| 单集 wall-clock | −15~25% |
| 协调损耗 | 8–15%（稳定期），20–30%（前 3 集） |
| 维护面 | 双环境、双日志、路径映射、版本漂移、睡眠/同步故障、队列与心跳 |
| 是否解决瓶颈 | 否。瓶颈是 8 h i2v 与人工门禁 |

**替代动作（单机即可，收益更高）**

1. i2v 镜数 40 → 20：省约 4 h/集。
2. 编码改 NVENC：1–2 h → 0.4 h。
3. 静帧 API 并发提交：wall-clock 约减半。

**保留的能力**：需要时把某个 run 目录手搬到 Mac 跑 ASR/编码，跑完搬回。不做队列、不做协议、不做双端环境固化。

**重新评估的触发条件**：悬疑线恢复生产（两条线抢 GPU）／周产 ≥2 集／Mac 成为主力工作机／Windows GPU 升级到 24 GB 以上。
