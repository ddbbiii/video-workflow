# 小球线路入口

- 账号头像：已选定像素风「蓄力小球」，[正式头像 PNG](../../assets/小球/brand/avatar/小球头像-蓄力小球.png)。

- 现行规则：[小球线规则入口](../../rules/小球/README.md)；[运动、构图、声音与验收](../../rules/小球/production.md)。
- 当前候选：[300 层重力翻倍 480](episodes/20261124-rings-300-gravity480/README.md)，约 4 分 4 秒；待用户比较，未替代已认可 240 基线。
- 状态与进度：见 [LINE_STATE.md](LINE_STATE.md)。
- 已认可重力基线：[300 层向下重力 240](episodes/20261124-rings-300-gravity/README.md)，162.6 秒；只改变重力参数并重新对齐两类音效，完整检查通过，用户已认可；重力翻倍版单独试听。
- 当前完整试听：[300 层近景，碰撞与穿环分别发声](episodes/20261124-rings-300-sfx/README.md)，160 秒；沿 C 方向调整长轨迹稳定与平滑构图，无配乐，待用户审看。
- 当前运动实验：[固定近景三方案](episodes/20261124-motion-closeup/README.md)，每段 10 秒静音；推荐 C 的密集环、慢补层和平滑缺口变化，待用户看折返与构图，未定稿正式运动底座。
- 当前音乐实验：[librosa 拍点 A/B 对照](episodes/20261124-music-beat-comparison/README.md)，同画面与音效比较进度渐强和拍点渐强；本期建议保留进度渐强，待用户判断听感，未替换正式流程。
- 当前碰撞试片：[小球物理碰撞](episodes/20261123-sand-rings-physics-test/README.md)，约 17.05 秒；零重力近弹性小球、连续缺口、平稳补层及显式擦边脱困，待看反弹观感。
- 当前新演示：[1000 层流沙圆环音乐版](episodes/20261123-sand-rings/README.md)，约 34.57 秒；连续音乐在最后 10% 和 3% 逐级加强，1000 次穿层逐次触发老吴音效，待审看。
- 逐级合球开新一期：[制作模板与配置表](planning/LEVEL_EPISODE_TEMPLATE.md)；[JSON 配置模板](planning/level-episode.template.json)。
- 素材呈现参考：[角色剪影与表情球面两种方案](planning/TEXTURE_REFERENCES.md)。
- 定位：小球／物件滚落、连锁、物理巧合类竖版短视频；靠撞击、节奏和画面完成度留人，不依赖旁白。
- 当前工程：[十重圆环真实反弹测试](episodes/20261122-escape-rings/story/script-draft.md)；包含 Matter.js 共享轨迹与 Motion Canvas、p5.js、Pillow、PixiJS 四条独立静音对照，QA 见单集 `qa/render-comparison.md`。
- 桌面软件索引：Motion Studio 独立维护于 `../../../motion-studio/`，GitHub 私有仓库为 [ddbbiii/motion-studio](https://github.com/ddbbiii/motion-studio)。小球线只维护本入口索引与 `VIDEO_OUTPUT_SPEC.md`；每期只保存 `studio/episode.json`、`simulation/trace.json`、用户项目、素材与预览，不复制 Studio 应用源码。当前可导入测试工程：`episodes/20261122-escape-rings/`；音效测试素材：`episodes/20261122-escape-rings/audio/output/escape-rings-reversal-sfx.wav`。`simulation/trace.json` 由适配器读取，不拖入素材库。
- 目录：`episodes/` 放单集与调试工程；线路规则见 `../../rules/小球/`，与通用规则冲突时按用户批准的小球线规则执行。
- 当前圆环玩法交付：含碰撞与穿环两类音效的完整 MP4，无旁白、字幕或 SRT；不落成品库，详见线路规则。

目录布局真源：`../../indexes/DIRECTORY_STRUCTURE.md`；线路索引：`../../indexes/LINE_INDEX.md`。
