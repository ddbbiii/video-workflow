# 正文交付执行件

纯正文交付的机器门禁，对应 `rules/shared/delivery.md` 与 `rules/shared/srt.md`。

| 文件 | 用途 |
|---|---|
| `check_delivery.py` | 检查成片 + SRT：1 条视频流、0 音频流、0 字幕流；时长=帧数/帧率；SRT 从 0 开始、每条 ≤20 字、单行、不超出视频 |

## 用法

```powershell
python shared/workflows/body-only/check_delivery.py `
  --video <ep>/video/final/<线路>_<剧名>_正文_vN.mp4 `
  --srt   <ep>/video/final/<线路>_<剧名>_正文_vN.srt `
  --json  <ep>/qa/delivery.json
```

- `PASS` 才能交付；退出码非 0 逐条列出失败项。
- 不检查画面内容与像素白黑屏；像素扫描仍按 `rules/shared/delivery.md` §四单独跑。
- 旧成片若首条 SRT 从片头偏移开始（如 0.55 s），本工具会判 FAIL——这是预期的：旧成品不回改，新成品必须 0 起点。
