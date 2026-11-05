# 字幕门禁 v1（模式 A）

- 输入：`E:\program\1project\video\4\runs\20261103-gla-b01\subtitles\r4\body.srt`
- 旁白：`E:\program\1project\video\4\video\final\glacier-river_narration.wav`
- 条数：685

## G2 同步（cue 起点 vs ASR 首字）

- 中位误差：+0.504s；IQR：0.053s；|误差| P95：0.580s；最大：2.947s
- 全局校正：字幕整体前移 -0.504s
- 5 分钟分箱中位：{0: 0.495, 1: 0.507, 2: 0.5, 3: 0.502, 4: 0.507, 5: 0.504, 6: 0.515, 7: 0.578}
- 分箱漂移：0.083s（阈值 0.30s）

## G3 能量

- 起点前静音 >0.35s：0 条
- 终点后拖尾 >0.50s：1 条

## G4 断句/排版

- cue 级（过短/CPS/超宽/数字量词）：2 条
- 行级（折行后超宽/坏首尾/超 2 行）：0 条

## 结论

- REVIEW