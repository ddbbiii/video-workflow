# 小球线路状态

- 状态：`debugging`（调试中，2026-11-10 建线）
- 定位：小球／物件滚落、连锁、物理巧合类竖版短视频；一遍看完、撞击节奏、无旁白或极少旁白。
- 当前工程：`episodes/20261122-escape-rings/`（十重圆环首次接触即破横向测试）；Matter.js 共享轨迹通过 10/10 同事件帧反向 QA。技术路线暂定 Motion Canvas 第一、p5.js 第二、PixiJS 第三。Motion Studio 独立维护于 `../motion-studio/`，GitHub 私有仓库 `ddbbiii/motion-studio`；小球线仅保留入口索引与 `VIDEO_OUTPUT_SPEC.md`，单集通过 `studio/episode.json` 连接适配器并保存项目数据。Pillow 暂停迭代。
- 目标规格：1080×1920 竖版，抖音成品；单支时长与更新频率待首支成品后定。
- 规则／资产：`rules/小球/`、`assets/小球/` 尚未建立；建立前沿用 `rules/shared/video-workflow.md` 两道门禁。
- 交付：正文视频 + 同基名 SRT，一起留在单集 `video/final/`；不落成品库、不做片头/配音/字幕烧录（2026-11-14 全线路口径）。

## 已知限制

- 当前 Motion Studio 只接受已打包的 `matter-ring-escape-v1` 适配器；单集 manifest 可校验接入，但未知模型需先开发并打包对应运行时。Windows 实机验证尚未完成。
- 当前测试视频不是线路最终交付；线路常规静音视频与独立 SRT 交付规则不变。
