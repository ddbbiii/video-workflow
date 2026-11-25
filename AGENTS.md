# Workspace Instructions

## 后台检索

- 检索和读取网页素材默认在后台完成，不切换、打开或操作用户的前台浏览器窗口，以免影响其他工作。
- 后台渠道无法读取某网站时，换用其他后台来源或说明具体限制；只有用户明确要求展示网页时才使用前台浏览器。

## Image Generation

- For image generation, use the configured image-generation API key and the project's supported CLI/API workflow directly. Do not require the user to approve switching away from a built-in image-generation tool.
- Do not print, log, or expose API keys or other credentials. Read only the credential needed for the requested generation task.
- If the configured key or generation endpoint is unavailable, report the concrete blocker and continue with useful prompt or workflow preparation where possible.
- Follow repository-specific image-generation and asset-management rules when present. Do not overwrite existing assets unless the user explicitly requests replacement.

## 版本与上下文清理

- 重做、修订完成并验收后，只保留当前有效版本；主动删除被替代的旧成片、旧字幕、旧候选图、废弃稿和无用中间文件，并同步移除当前入口中的旧版引用。
- 不自动保留备份、归档或为旧生成物创建 Git 快照；仅保留当前生产依赖、有效角色参考和简明 QA。用户明确要求保留时例外。
- 当前状态文档直接更新到最新结果，不叠加过时状态、失败尝试和版本演进记录，避免污染上下文。

## 配音确认门禁

- 开始制作最终视频或最终 SRT 前，必须先向用户确认本期剪映配音使用的具体音色；同时确认配速，或明确沿用已确认的配速基准。
- 未得到用户明确答复前，不开始最终视频/SRT 的时间轴定稿与产出。用户明确授权本期跳过确认时，按该授权执行。
- 用户指定音色后，按该音色的实际朗读时长校准 SRT 与镜头时间轴；段间保留约 0.2 秒自然衔接，句内停顿按语义保留，不把所有低音量区都当作可删除静音。
