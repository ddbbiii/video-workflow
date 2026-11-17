# 拟人形态：双足街舞猫（biped）

- 建立：2026-11-09，为「舞蹈 / 动作迁移」内容准备
- 用途：Wan2.2 Animate 的角色参考图；四足实拍形态无法套人骨架，动作迁移必须用这个形态
- 与本体关系：脸、毛色、臭脸神情沿用 `CHARACTER_SPEC.md` 的银渐层锚点；身体改为人形比例

## 造型

- 头：波斯系扁圆脸、金琥珀眼、额 M 纹、白毛领、小圆耳
- 身：人形躯干与四肢，深灰卫衣（oversized）+ 深灰工装裤 + 白色厚底鞋，细银链项链
- 尾巴：蓬松大尾外露，作为辨识点
- 气质：臭脸、松弛、有点拽

## 文件

| 文件 | 用途 |
| --- | --- |
| `concept_front.png` | 正面全身概念图（896×1216，Z-Image Turbo，8 步） |
| `ref_16x9.png` | 832×480 横版首帧参考，Animate 每段都用它 |
| `concept_prompt.txt` | 概念图提示词原文 |

## 生成约定

- 概念图：Z-Image Turbo，`qwen_3_4b` 文本编码 + `ae` VAE，ModelSamplingAuraFlow shift 3，8 步 / cfg 1.0 / res_multistep+simple
- 动作迁移：Wan2.2 Animate 14B int8 + lightx2v 4-step LoRA，832×480 / 77 帧 / 6 步 / euler+simple / shift 8
- 参考图必须是 16:9 且角色居中留边（`ref_16x9.png`），否则首帧会被裁切、开局出现推镜

## 已知问题

- 倒立、地板动作时四肢和头部会糊，剪短切可掩盖
- 每段开头约 0.3–0.5 秒是参考姿势站定，剪辑时剪掉
- 嘴部在发力时会张得偏大，必要时用反应镜头替换
