# 助眠解说 · 执行件索引

> 本目录只放可复用的脚本、配置样例与命令，不放规则。规则真源：`rules/助眠解说/`。
> 2026-11-06 精简：历史说明与 legacy 细节移入 `shared/archive/design/`。

## 可复用工艺

| 目录 | 内容 | 规则 | 入口 |
|---|---|---|---|
| `intro-v5-stacked/` | 短标题型三句堆叠片头（10–12 s）＋ DP 字幕重对齐参考 | `rules/助眠解说/intro.md` §6 | `reference_build_intro_v2.py`、`reference_realign_subtitles.py` |
| `hook-intro-v1/` | Hook 型（两拍钩子＋四字标题＋ASS 矢量动画，30–35 s，**新单集默认**） | `rules/助眠解说/intro.md` §7 | `reference_hook_intro.py <config.json>` |

## 目录约定

```text
shared/workflows/助眠解说/
  README.md                 本索引
  intro-v5-stacked/         片头模板 + 参考实现
  hook-intro-v1/            片头模板 + 参考实现 + 配置样例
  b-geomagnetic-reversal/   历史存档（地磁单集 81 个脚本），不作新单集模板
```

## 说明

- `b-geomagnetic-reversal/` 是 2026-10-08 从 legacy 迁入的完整脚本集，路径与依赖按当时状态保留；细节见 `shared/archive/design/workflows-readme-legacy-20261106.md`。新单集不要复制它。
- 执行件里的绝对路径按需保留（Windows 环境），跨机运行时改配置，不改脚本。
- 新增工艺：新建子目录 + 在本表加一行，并在 `rules/助眠解说/README.md` 的模块表登记对应规则。
