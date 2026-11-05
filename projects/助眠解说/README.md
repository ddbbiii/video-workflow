# 助眠解说入口

后期分工：用户手动混合配音/BGM，并用 Subtitle Edit 生成、校准字幕。助手交付独立素材，等待用户交回最终混音和字幕；不默认自动混音或 ASR。真源：[手动后期](../../rules/shared/audio/manual-post-production.md)。

账号名：**星夜慢谈**。识别资料与定稿状态见 [账号识别](../../rules/助眠解说/account-identity.md)。

封面规范真源：[助眠封面流程](../../rules/助眠解说/covers.md)。默认横竖分别构图，中央或中上大标题主导，延续蓝金电影感；字号和占幅按标题长度调整，地磁 r2 参数仅供参考。交付封面时同步提供发布标题、标签与简介。

字幕规范真源：[字幕工作流](../../rules/助眠解说/subtitles.md)；批准样式为 style_r4。字体/许可资产见 [字幕资产](../../assets/助眠解说/subtitles/style-r4/CURRENT.md)，单集未决事项见 [地磁字幕收尾](../../todos/助眠解说/地磁字幕收尾.md)。旧交接记录不替代当前线路规则。

当前状态见 LINE_STATE.md；共用规则见 ../../rules/shared/，线路规则见 ../../rules/助眠解说/。可复用角色、声线、场景和道具见 ../../assets/助眠解说/。

助眠专属片头真源：[片头规则](../../rules/助眠解说/intro-node.md)。先锁最终配音，再按 sample 边界排片头画面和艺术字；正文字幕与 BGM 仍由用户手动完成。具体视觉结构按主题选择，不使用旧片头参数或字符比例估时。

- episodes/：新单集任务。
- characters/：角色资料。
- assets/：资产索引和参考资料。
- drafts/：未锁定草稿。
- logs/：运行记录。
- shared/archive/：旧版本与暂停内容。

已有其他子目录按原职责保留；目录布局见 ../../indexes/DIRECTORY_STRUCTURE.md。资产验收以项目状态和 manifest 为准。
