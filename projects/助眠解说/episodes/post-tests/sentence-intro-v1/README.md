# 整句大字幕视频片头试样

当前迭代 v6b：配置 `config-v6-video-pool.json`，输出 `render-v6b-video-pool/sentence-intro-preview.mp4`。从全套正文通过版镜头池按 seed 42 随机抽取，先排除时长不足的镜头，不按图生视频/图片运镜分类限制；保留视频原始运动，不叠加背景缩放。每句 4 秒，文字淡入/淡出各 1 秒，完整显示 2 秒，文字缓慢从 96% 放大至 102%。1080p60 仅保证新增文字动画按 60 fps 渲染，源素材不补帧。此为有片头设计文字的内部审核样片，不代表无字幕正式交付被取消。`render-v6-video-pool/` 是因候选时长不足中止的内部诊断批次，不作交付。

1080p60 对照配置：`config-1080p60.json`，输出到 `render-v5-1080p60/`。相同素材、台词、seed 和时长，1920×1080、60 fps、CRF 17；直接解码源视频而非放大旧试样。仅新增运镜/文字按 60 fps 计算，不进行光流或 AI 补帧，不声称提升原视频内部运动帧率。实际源分辨率与帧率记录在 manifest。

```powershell
python shared/compositing/build_sentence_intro.py --config projects/助眠解说/episodes/post-tests/sentence-intro-v1/config-1080p60.json
```

2026-10-12 抖动修正版：当前审核候选为 `render-v4/sentence-intro-preview.mp4`。用浮点亚像素 affine 替换 zoompan 整数裁切；文字一次固定排版后整层动画，避免逐帧排版变化；推拉、文字缩放和淡入使用 smoothstep 缓动。原视频动态保留。ASS 仅记录文字与时间参考，实际渲染使用独立固定文字图层。旧版留存，不据数值或解码通过声称肉眼无抖动，最终需播放审核。

状态：视觉试听待审核，不替代已批准的正式片头规则。试样约 12 秒、1280×720、30 fps，无音轨；三句话各占一段正文视频，居中两行，短促放大收拢与渐显后固定，不滚动。不新增图片、不调用生成 API、不使用 GPU 推理。

当前示例：`render-v3/sentence-intro-preview.mp4`。在连续视频上附加缓慢推近/拉远/推近，幅度 8%；文字 650 ms 淡入，整句期间从 92% 缓慢放大至 104%，不使用冲击收拢。视频运动保留，不使用静态帧替代。源素材与裁切位置见对应 `manifest.json`；旧版保留于 `render/`、`render-v2/`。素材从地磁正文 clips/final_r2 固定 seed 抽取，正式使用时必须复核主题对应关系，并避免附加推拉与源视频运动冲突。

脚本：`shared/compositing/build_sentence_intro.py`；本目录 `config.json` 指定素材目录、seed、台词和每句时长。运行：

```powershell
python shared/compositing/build_sentence_intro.py --config projects/助眠解说/episodes/post-tests/sentence-intro-v1/config.json
```

重跑需指定新输出目录，脚本不覆盖已有文件。正式配音确定后按实际句子边界填写时长；当前每句 4 秒仅为视觉演示，不声称与重音同步。强音效和音乐由用户手动后期处理，本轮未制作。正式最终输出仍遵循两个文件规则；此处是内部审核试样。
