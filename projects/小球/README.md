# 小球线路入口

- 状态与进度：见 [LINE_STATE.md](LINE_STATE.md)。
- 定位：小球／物件滚落、连锁、物理巧合类竖版短视频；靠撞击、节奏和画面完成度留人，不依赖旁白。
- 当前工程：[十重圆环真实反弹测试](episodes/20261122-escape-rings/story/script-draft.md)；包含 Matter.js 共享轨迹与 Motion Canvas、p5.js、Pillow、PixiJS 四条独立静音对照，QA 见单集 `qa/render-comparison.md`。
- 桌面软件索引：Motion Studio 独立维护于 `../../../motion-studio/`，GitHub 私有仓库为 [ddbbiii/motion-studio](https://github.com/ddbbiii/motion-studio)。小球线只维护本入口索引与 `VIDEO_OUTPUT_SPEC.md`；每期只保存 `studio/episode.json`、`simulation/trace.json`、用户项目、素材与预览，不复制 Studio 应用源码。当前可导入测试工程：`episodes/20261122-escape-rings/`；音效测试素材：`episodes/20261122-escape-rings/audio/output/escape-rings-reversal-sfx.wav`。`simulation/trace.json` 由适配器读取，不拖入素材库。
- 目录：`episodes/` 放单集与调试工程；规则、资产暂未建线，先用 `../../rules/shared/` 通用流程与门禁。
- 交付：正文视频 + 同基名 SRT，一起留在单集 `video/final/`；不落成品库、不做片头/配音/字幕烧录。

目录布局真源：`../../indexes/DIRECTORY_STRUCTURE.md`；线路索引：`../../indexes/LINE_INDEX.md`。
