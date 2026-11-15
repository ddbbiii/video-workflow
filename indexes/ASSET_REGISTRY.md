# 资产目录入口

> 2026-11-14：纯正文口径。配音、BGM、字幕样式资产不再参与生产，仅作存档；不要再把它们当默认素材。

## 在用

- 全部线路复用资产：`assets/对应线路/`。
- 悬疑角色三视图与 CHARACTER_SPEC：`assets/悬疑/characters/<character_id>/`（规则 `rules/悬疑/visual.md` §六；主角先判弱复用，三视图未锁定不得批量生图）。
- 悬疑 20261110-pool 角色：`zhouxu-20261110-pool`、`zhounian-20261110-pool`（A 档 2×2 三视图）、`lifang-20261110-pool`、`zhoujianguo-20261110-pool`、`lindeshun-20261110-pool`（B 档单张参考）。
- 人生体验主角定装：`assets/人生体验/characters/catman-20261113/`（三视图、表情图、脸裁切参考图、用户原图）。
- 萌宠角色卡：`assets/萌宠/characters/silver-grumpy/`（身份卡 + 参考图清单 + 实拍 10 张）。
- 悬疑风格 LoRA：`assets/悬疑/styles/rainnight/style-suspense-rainnight-sdxl-v1.safetensors`。
- 小球、助眠解说：线路资产按需建立，建立后在 `indexes/ASSET_REGISTRY.md` 登记。

## 存档（不参与当前生产）

- 字幕样式 `assets/shared/subtitles/style-r4/`：只作 SRT 行宽测试的字体来源；不再烧录。
- 助眠统一 BGM `assets/助眠解说/audio/bgm/`、悬疑 BGM `assets/悬疑/audio/bgm/`：用户自行处理音频，助手不选曲、不混音。
- 悬疑恐怖人声库 `assets/悬疑/audio/vocal/`：原用于片头，现已停用。
- 助眠旧声线 / 悬疑女声候选：已移入 `shared/archive/voices-pruned-20261112/`，不再作候选。
- 历史共用资产：`shared/archive/`；退役线路资产在 `shared/archive/retired-lines-20261110/`。

路径相对于 `E:/program/1project/video`。验收以 manifest、CURRENT.md、项目状态为准；迁移不改变批准状态。
