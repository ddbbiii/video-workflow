# 逐级合球成片

竖屏 1080×1920、30 fps。Level 1 是基础球；两颗同级球碰撞合成为下一级，达到 Level 8 后停止投放并播放结尾特效。小球每 0.3 秒从烧瓶瓶口同一点落下，每级直径增大 20%。

- 当前成片：[透明猫脸剪影版](video/final/cat-faces-character.mp4)，时长约 49.75 秒。
- Level 1–5 使用本期生成的正面透明猫脸，Level 6–8 沿用已确认素材；八级预览见 [图片与音效关系图](assets/cat-faces/ai-frontal-v1/level-audio-map-1-8.png)。贴图在 `assets/cat-faces/ai-frontal-v1/textures/`。
- 两颗同级球合并时增加两帧渐进接触挤压反馈，随后显示合成结果；最终 Level 8 保留专属碰撞停留、粒子与多层光圈。
- Level 1 无合成音效；Level 2–8 依次使用老吴 `07、08、09、10、11、01、05.wav`。Level 8 音效开始时截停其他音效，并屏蔽其后的低级合并声。
- 物理轨迹：[trace.json](simulation/trace.json)，生成脚本：[generate_trace.mjs](simulation/generate_trace.mjs)。音效：[render_sfx.mjs](audio/render_sfx.mjs)，画面：[index.html](renderers/canvas/index.html)。
- QA：视频为 H.264/AAC，1080×1920、30 fps；音画时长一致，最终 Level 8 画面持续到音效尾声结束。
