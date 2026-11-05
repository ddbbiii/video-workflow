# 工作区地图与整理记录

> 盘点：2026-11-05　整理执行：2026-11-05 → 11-06
> 当前总量：**483 GB**（整理前约 572 GB，净回收 **89 GB**）
> 真源：`indexes/DIRECTORY_STRUCTURE.md`（本文件只做现状快照，不改规范）

## 1. 顶层现状

| 目录 | 体积 | 定位 |
|---|---:|---|
| `shared/` | 420 GB | 运行时、模型、工具、工作流、交换区、成片归档 |
| `projects/` | 51 GB | 线路与单集 |
| `4/` | 7.7 GB | glacier-river（已交付 v1.1） |
| `编剧3/` | 2.5 GB | life-manual（已交付 v1） |
| `FindCity_AI_Photo_Library/` | 1.0 GB | 城市照片库（非视频线路） |
| `assets/` | 0.5 GB | 可复用素材 |
| `5/` | ~0 | 生日悖论（仅剧本） |
| `rules/` `indexes/` `todos/` | ~0 | 规则、索引、待办 |
| `work/` | 0 | 空壳 |
| 根文件 | 0.95 GB | `README.md`、`FindCity_AI_Photo_Library.7z` |

## 2. 空间构成

| 块 | 体积 | 说明 |
|---|---:|---|
| `shared/runtime` | 265.6 GB | ComfyUI 184.4（models 173.1）＋ engines 80.2（stills 49.2、tts 31.0） |
| `shared/lip-tools` | 128.7 GB | 口型/换脸工具链与模型 |
| `shared/project-tools` | 15.5 GB | 工具、ComfyUI 用户目录、训练脚本 |
| `shared/archive` | 9.3 GB | 历史归档 |
| `projects/助眠解说` | 42 GB | 六个单集的素材与工程（成片已移出） |
| `shared/delivery` | 25.4 GB | 成片归档（finals 14.82 + uncertain 10.62） |
| `4/` + `编剧3/` | 10.2 GB | 两部已交付长片（成片已移出） |
| `projects/悬疑动漫` | 6.4 GB | 已暂停线路 |
| 其余 | ~8 GB | 创意、猎奇、assets、exchange |

## 3. 成片归档（2026-11-06 建立）

```text
shared/delivery/
  finals/       15 个确认终版，14.82 GB，命名 <episode>_clean.mp4 / _sub.mp4
  uncertain/   224 个待定，10.62 GB，保留原相对路径
  MANIFEST.md   逐文件来源、命名规则与处理方式
```

- 生产目录（`projects/`、`4/`、`编剧3/`）里的视频文件已清空：**剩余 0 个**。
- 删掉的确定非终版：**822 个 / 1.02 GB**（逐镜片段、分段、预览、草稿、review 工作件）。
- 流水：`shared/archive/maintenance/organize-20261106.jsonl`。

## 4. 执行汇总

| 日期 | 动作 | 结果 |
|---|---|---|
| 11-05 | 删旧片（每部只留 clean/sub） | 5,596 个 / 88.3 GB，0 失败 |
| 11-05 | 清 `__pycache__` | 7,504 个目录 / 1.07 GB |
| 11-05 | 清空目录 | 119 个 |
| 11-06 | 归位终版 | 15 个 → `shared/delivery/finals` |
| 11-06 | 归位待定 | 224 个 → `shared/delivery/uncertain` |
| 11-06 | 删确定非终版 | 822 个 / 1.02 GB |
| 11-06 | 清空目录 | 90 个 |

审计清单：`shared/archive/maintenance/deleted-videos-20261105.jsonl`、`organize-20261106.jsonl`。

## 5. 待你决定

| 项 | 情况 |
|---|---|
| `uncertain/` 里章鱼、蟑螂的 4 个重做/对照母版（8.78 GB） | 确认后移入 finals 或删除 |
| `uncertain/` 里旧线路 220 个整片候选（1.85 GB） | 悬疑/创意/猎奇/外卖之谜，命名带 final 但无 clean/sub 配对 |
| `4/` `5/` `编剧3/` 根目录归属 | 规范要求根目录只 6 项，但两份 PROJECT_STATE 写明「用户指定命名」；迁移需改引用 |
| `FindCity_AI_Photo_Library.7z`（0.95 GB） | 与同名目录疑似重复 |
| `shared/runtime` 265.6 GB ＋ `lip-tools` 128.7 GB | 多套 ComfyUI/模型，需 hash 清单后去重 |

## 6. 后续

1. `uncertain/` 逐项拍板。
2. `4/5/编剧3` 定例外或迁移。
3. 运行时模型去重（等 Mac 并行跑起来、模型可分流后再做）。
4. 工作流拆分到 Mac：待分析（用户表示后面再进一步拆解）。
