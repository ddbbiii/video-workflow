# 图片 API 备选与切换（shared/image-api）

**通道路由的唯一事实源是 `channel-policy.json`**（含通道、单价、路由、门禁阈值、启停条件）。
规则文档（`rules/shared/video-workflow.md` §4、两线 `visual.md`、`image-grid-generation.md`）
只写原则，改阈值/启停只改策略文件并升 `version`。

当前 `active = v7-new2-dklb-parallel`（2026-11-15）：`new2`（0.018 元，1672×941）与 `dkl-b`（0.018 元，2048×1152）按镜头轮询、两队并发；同一集可混合通道，单次图片/网格请求只走一个通道。单通道失败只转移失败/未开始镜头，已完成镜头不重跑；两通道都不可用时停止剩余任务。`old`（0.16 元）仅人工质量救援。

> 2026-11-12 三题对比（2x2 网格 / 证据特写 / 人物全身）结论：dkl2 与 old 同质
> （1080p 感知锐度 G 103 vs 110、S2 32 vs 27、S1 19 vs 17），单价 1/10；
> new2 在 1080p 与两者持平但原生只有 1672×941。完整报告与对照图见
> `runs/20261112-113201-channels-3way/`（脚本 `compare_channels.py`，可 `REUSE_RUN` 续跑）。
> `yy` 的 key/站点均通、模型可列，但账户余额 `$0.000000`，2026-11-11 / 11-12 三次探测
> 均 403 `insufficient_user_quota`，**尚不能出图**；充值后同一脚本直接加列对比即可。

> 2026-11-12 画风校准（悬疑）：同题 3 镜（走廊 / 人物背影 / 证据特写）跑 dkl2 / new2 / old，
> 提示词取 `rules/悬疑/visual.md` §二 的 `STYLE_POS` + `STYLE_NEG`（`Avoid:` 追加）。
> 结论：**dkl2 默认**；空镜用 `STYLE_POS`，**含人物/手部/证据特写加 `CEL_BOOST`**（dkl2 加后
> 2048 原生达到赛璐璐）；`new2` 只兜底（1672×941、饱和偏高）；`old` 只救援（偏半写实、165 s+、0.16 元）。
> 报告 `runs/20261112-133807-style-calib/VERDICT.md`，脚本 `calibrate_suspense_style.py`。

> 路由函数 `client.pick_channel()` 尚未实现；在此之前按决策卡
> （`runs/20261109-080000-split-plan/WORKFLOW_ROUTING.md` §四）人工执行并按 §二 记录，
> 不要各脚本自行判断通道。

本目录存放备选通道的探测脚本、对照实验与决策记录；旧通道 `dklapi` 的 key/url 保持不变，可随时回滚。

## 备选：mxwell（2026-11-09 探测，已充值有额度）

| 项 | 值 |
| --- | --- |
| Base URL | `https://api.mxwell.ai/v1`（用户环境 `IMAGE_API_BASE_URL_MX`） |
| Key | 用户环境 `IMAGE_API_KEY_MX`（未落仓库、未写进任何脚本） |
| 模型列表 | `gpt-image-2`、`gpt-image-2.5`、`gpt-image-2.5-flare`、`gpt-image-2.5-sunburst`、`gpt-image-2.6`、`gpt-image-2.6-flare`、`gpt-image-2.6-sunburst` |
| 接口 | `POST /v1/images/generations`、`POST /v1/images/edits`（均验证通过） |
| 取图 | 内联 `b64_json`（老站是 CDN URL 二次下载） |

### 接入注意

- **Cloudflare 拦默认 UA**：`Python-urllib/3.11` 触发 `Error 1010 browser_signature_banned`（403）。
  脚本必须显式带 `User-Agent`（本目录脚本用 `OpenAI/Python 1.60.0`），否则会被误判成接口挂了。
- 路径必须是 `/v1/images/generations`；写成 `/v1/generations` 返回 `Invalid URL`。
- `edits` 在**没有 image 字段**时不报错，会静默按文生图出图 —— 上传参考图的脚本必须校验
  multipart 里 `image` 真的带上，否则会悄悄变成 txt2img。
- `GET /v1/dashboard/billing/subscription` 返回的是套餐上限（plan `mxwell`，1e8），
  **不是可用余额**，别拿它当余额核对。

## 备选二：xxcapi（2026-11-09 探测）

| 项 | 值 |
| --- | --- |
| Base URL | `https://xxcapi.com/v1`（用户环境 `IMAGE_API_BASE_URL_XXC`） |
| Key | 用户环境 `IMAGE_API_KEY_XXC` |
| 可用模型 | 该 key 属 `codex专属生图` 分组，只有 `AZ-gpt-image-2`、`AZ-gpt-image-2.5-flare`、`AZ-gpt-image-2.5-sunburst`；`gpt-image-2.5-sunburst` 报 `model_not_found`，1K/default 组 503 |
| 输出尺寸 | **固定 1672×941**（请求 2048×1152 无效） |
| 单价 | 实测 3 次扣 5.33 美分 ≈ **0.018 元/次**（与 mxwell 同 1:1 口径） |

**用途判断**：单镜（人物/证据/道具特写）1080p 交付锐度 86.7，接近 dklapi 的 91.0；
但 2×2 网格拆四格只剩 836×471，放大到 1080p 后与 mxwell 打平（26.9 vs 24.7），不适合网格。

## 候选三：yy.shagentai.com（2026-11-12 复核，key 通、账户仍 $0）

| 项 | 值 |
| --- | --- |
| Base URL | `https://yy.shagentai.com/v1` |
| Key | 用户 2026-11-12 直接给的新 key，按约定只走用户环境变量 `IMAGE_API_KEY_YY`，不落盘、不打印 |
| 模型列表 | 本 key 6 个：`gpt-image-2-cdn`、`gpt-image-2.5`、`gpt-image-2.5-cdn`、`gpt-image-2.5-flare-adx2`、`gpt-image-2.5-flare-cdn`、`gpt-image-2.6-cdn`（11-11 的另一个 key 曾列出 32 个） |
| 接口 | `/v1/models`、`/v1/dashboard/billing/*`、`/v1/images/generations` 路径均可达；鉴权有效 |
| 余额 | **＄0.000000**，`total_usage` 也是 0：任一模型生成都立刻 403 `insufficient_user_quota`（11-11 与 11-12 共三次探测一致） |
| 结论 | 站点和 key 本身是通的，但账户没充值，无法参与 2026-11-12 三题对比（未产生费用） |

脚本：`probe_yy.py --models`（免费列模型）、`probe_yy.py`（A = 热液四格，与 11-09 三站 A/B 完全同词，锐度可直接对比；B = 天文台四格，换题材看高光/金属结构/无文字仪表）、`yy_balance_check.py`（余额 + 其它模型分组）。充值后也可直接加 `CHANNELS` 跑 `compare_channels.py`，与 new2 同题对比。

## 已退役：DKL 第二把 key（0.015 元，dkl2）

2026-11-12 短暂试用过 dklapi 的另一把 key（`dkl2`，0.015 元/张），当天即由用户决定**删除 key、不再维护**：
各 4 样本复核显示它把 1K 渲染铺到 2048 画布（等效原生 ~1280），写实题材交付与 new2 打平、
动漫题材只及 new2 的 1/2。`channel-policy.json` 里该通道已标 `retired-2026-11-12`，
active 回到 `v5-new2-old`（new2 主用、old 兜底）。

存档：`runs/20261112-114824-dkl3way-2x2/REPORT.md`、`REPORT-repeats.md`，脚本
`compare_dkl_new_three.py` / `probe_dklnew_res.py` / `repeat_samples.py` / `aggregate_repeats.py`
（仅作历史记录，需 `IMAGE_API_KEY_DKL2`，该变量已删除，不会再跑通）。

## 三站对比结论（2026-11-09）

| | dklapi | mxwell | xxcapi |
| --- | --- | --- | --- |
| 单价 | 0.16 元 | 0.02 元 | 0.018 元 |
| 输出 | 2048×1152 精确 | 2048×1152（偶发 2016） | 固定 1672×941 |
| 网格格子→1080p 锐度 | **73.8** | 24.7 | 26.9 |
| 单镜→1080p 锐度（悬疑 S1） | **91.0** | 50.6 | **86.7** |
| 手部/三视图 | 好 | 差/漂移 | 基本可用 |

分工建议：助眠环境格走 mxwell、特写走 dklapi；悬疑单镜走 xxcapi、三视图与网格走 dklapi。

### 长期只留一个：选 xxcapi（2026-11-09 加测 6 次）

同提示词补测 S1 复抽 / S2 证据 / S4 门锁，交付 1080p 锐度：

| 镜 | mxwell | xxcapi |
| --- | --- | --- |
| S1b 持钥匙（复抽） | **12.0**（且尺寸变 2016，近似废图） | **73.0** |
| S2 证据特写 | 37.2 | **101.0** |
| S4 门锁特写 | 112.3 | **215.1** |

mxwell 8 次抽样里出现 2 次近糊废图（lap 5.9 / 11.2）与 2 次尺寸变 2016；xxcapi 3 次全部
1672×941 稳定。**结论：长期第二通道选 xxcapi**（0.018 元），mxwell 降为备用。
代价：xxcapi 固定 1672×941，不能出 2048；该 key 只有 AZ 型号；大推近慎用。



同模型 `gpt-image-2.5-sunburst`、同尺寸 `2048×1152`、同提示词（深海热液四格：三烟囱广角 /
五只管虫微距 / ROV 机械臂夹矿石 / 喷口边缘四虾），各 1 次调用：

| 项 | OLD · dklapi | NEW · mxwell |
| --- | --- | --- |
| 耗时 | 34.1 s | **27.9 s** |
| 尺寸精确度 | 2048×1152 | 2048×1152 |
| 锐度（拉普拉斯方差） | **839** | 311 |
| 锐度（P3/P4 格） | **1155 / 888** | 249 / 198（−78%） |
| 饱和度 | 85–121 | 136–155（偏暖艳） |
| 高光裁切 | **0.07%** | 0.42% |
| P2 微距管虫可读性 | 前景失焦体占 1/4 画面 | **更干净（此格胜）** |

结论：不能**无差别**替换。NEW 在暗部纹理、硬表面机械结构、微距细节上系统性偏软，色温偏暖、
高光更易死白；环境/远景/低细节格子可接受（P1 观感接近），特写与机械结构仍应走 OLD。
完整报告：`runs/20261109-063916-grid2x2-ab/REPORT.md`（含 100% 放大对照图）。
`quality: "high"` 不能补上差距（NEW high 更软，lap_var 233）。

补充发现（同日追加，各 1 次调用）：

- 换 2.6 系列无效：OLD `2.6-sunburst` 703、NEW `2.6` 331、NEW `2.6-sunburst` 270（基准 839/311）。
- `2.5-flare` 是另一套极平滑画风且**尺寸不达标**（2048→2016），不要用于生产。
- **NEW 的有效细节上限约 1024 级**：请求 4096×2304 实得 4032×2304，lap_var 仅 13.6（≈1/16），
  即低分辨率渲染后放大；请求 1024×576 时 per-pixel 最锐（443 / 1.38）。**尺寸上限压到 2048×1152。**

## 价格与选型（2026-11-09 用户确认：NEW 0.02 元/张，OLD 0.16 元/张，8 倍）

| 方案（按 60–85 次/集） | 单集成本 | 相对全 OLD |
| --- | --- | --- |
| 全 OLD | 9.6–13.6 元 | — |
| 全 NEW | 1.2–1.7 元 | −87% |
| 75% NEW + 25% OLD | 3.6–5.1 元 | −63% |

建议"NEW 默认 + OLD 例外"：机械/仪器结构特写、微距、母题定装、明显推近的关键特写仍走 OLD；
其余环境与氛围格走 NEW，并加统一色温/饱和校正（NEW 偏暖偏艳、暗部有色带）。

## 2026-11-12 四通道对比（dkl2 转正；yy 未充值）

同模型族、同提示词各 1 次调用（无重试）：G = 2x2 深海四格（11-09 基准原词），
S2 = 证据特写（手/纸/浅景深），S1 = 人物全身（持钥匙的手）。报告全文
`runs/20261112-113201-channels-3way/REPORT.md`，对照图 `compare/sheet-*.png`。

| 通道 | 单价 | 原生尺寸 | G 感知锐度 | S2 | S1 | 可用性 |
| --- | --- | --- | --- | --- | --- | --- |
| old（dkl 旧 key） | 0.16 元 | 2048×1152 | 110.0 | 26.9 | 17.2 | 可用 |
| **dkl2（dkl 新 key）** | **0.015 元** | 2048×1152 | 102.7 | 31.7 | 19.4 | 可用 |
| new2（xxcapi） | 0.018 元 | 1672×941 | 113.4 | 27.7 | 19.9 | 可用 |
| yy（shagentai） | 待核价 | 2048×1152 | — | — | — | **403，余额 $0** |

口径：先统一缩到 1920×1080，再 0.8 px 高斯去噪后算拉普拉斯方差。直接用原生 lap_var 会被
颗粒噪点抬高（old 744 / dkl2 378 的差距主要是噪点，不是细节），不能当清晰度用。

- **dkl2 与 old 同质**：同站同模型，构图/画风接近，2048 原生；价格 1/10，故设为默认。
- **new2** 在 1080p 上与两者持平，且最贴"赛璐璐"要求；但原生 1672×941，网格拆格只有 836×471。
- **dkl2 / old 返回 CDN URL**（不是 b64），下载会卡；`compare_channels.py` 已改用 curl 断点续传。
- **yy** key 与站点都通、能列 6 个模型，但账户 `$0.000000`，三次探测均 403；充值后把
  `CHANNELS` 里的 yy 打开重跑即可，不需要改代码。

## 脚本

```powershell
python shared/image-api/probe_mxwell.py --check   # 免费：鉴权 + 模型列表
python shared/image-api/probe_mxwell.py           # 冒烟 -> 生产尺寸 -> edits 三项探测
python shared/image-api/compare_grid_2x2.py       # 同提示词 2x2 新旧 A/B + 裁格 + 对照图
python shared/image-api/crispness.py              # 锐度/对比度/裁切指标
python shared/image-api/edits_ref_test.py         # 参考图 edits 是否真的生效
python shared/image-api/quality_high_test.py      # quality=high 对照
python shared/image-api/grid_model_test.py        # 2.6 / flare 模型矩阵对照
python shared/image-api/native_size_probe.py      # 1024/1536 原生尺寸探测
python shared/image-api/size_test.py              # 4096 是否真渲染（放大测试）
python shared/image-api/delivery_res.py           # 1080p 交付分辨率 + USM 复盘
python shared/image-api/compare_channels.py       # dkl2 / new2 / old / yy 同题对比（断点续跑）
```

- key 读取顺序：环境变量 `MXWELL_API_KEY` → 用户环境 `IMAGE_API_KEY_MX`；不打印、不落盘。
- 产物在 `runs/<时间戳>-*/`（已 gitignore）：原始响应、出图 PNG、裁格、指标、`REPORT.md`。

## 转正条件（缺一不可）

1. 用户确认分工（NEW 只跑环境/远景，或整体替换）与 mxwell 实际单价（OLD 按 0.16 元/张计）。
2. 真实单集混跑一次：NEW 格加锐化 + 压高光/降饱和后处理，逐格复检暗部色带与文字禁令。
3. 用户确认后，才改 `rules/shared/video-workflow.md` 与各集生图脚本；旧 key/url 保留可回滚。

