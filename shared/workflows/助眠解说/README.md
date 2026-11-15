# 助眠解说 · 执行件索引

> 本目录只放可复用的脚本、配置样例与命令，不放规则。规则真源：`rules/助眠解说/`。
> 2026-11-14：配音（TTS）、片头执行件全部移入 `E:\program\1project\video-archive\20261114-body-only\workflows-obsolete\`，默认不读。

## 可复用

| 目录/文件 | 内容 |
|---|---|
| `EPISODE_INPUT_TEMPLATE.md` | 单集输入单（9 行：4 必填 + 5 选填） |
| `b-geomagnetic-reversal/` | 历史存档（地磁单集脚本），不作新单集模板 |

## 已归档

- `voice-cosy3/`（TTS）、`intro-e/`、`hook-intro-v1/`、`intro-v5-stacked/`：随规则废止移出。
- 需要恢复时从归档目录整体搬回，并在 `rules/shared/README.md` 登记；默认不恢复。

## 目录约定

```text
shared/workflows/助眠解说/
  README.md                 本索引
  EPISODE_INPUT_TEMPLATE.md 单集输入单
  b-geomagnetic-reversal/   历史存档
```

- 执行件里的绝对路径按需保留（Windows 环境），跨机运行时改配置，不改脚本。
- 新增工艺：新建子目录 + 本表加一行，并在 `rules/助眠解说/README.md` 登记。
