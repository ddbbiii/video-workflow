# 生产锁定 · 程雾+毛衣女同框 v4（B2）

- 锁定时间：2026-09-23（用户确认「没什么问题了」）
- 产出：`C:\Users\10060\Desktop\grok-bot-xfer\keyframes-2026-09-23\chengwu-sweater-v4-B2\`
- 脚本：`smoke_chengwu_sweater_v4_B2.py`

## 权重
| 角色 | 文件 | model/clip |
|------|------|-----------|
| CKPT | animagine-xl-4.0-opt.safetensors | — |
| 程雾 | chengwu-sdxl-v1b.safetensors | 0.78 / 0.72 |
| 毛衣女 | charb-sweater-sdxl-v1b.safetensors | 0.72 / 0.66 |
| 家景 | jiaoli-home-sdxl-v1.safetensors | 0.70 / 0.62 |

## IP-Adapter
- 风格：ip-adapter-plus_sdxl_vit-h，weight 0.22，style transfer，end_at 0.55，锚 `style-prev-N2.png`（旧定妆）
- 锁脸：ip-adapter-plus-face_sdxl_vit-h，weight 0.70，linear，end_at 0.85，左右 SolidMask+FeatherMask
- 程雾脸：`chengwu_identity_upperbody_A.png`
- 毛衣女脸：Grok 风格统一第2张 → `v4-face-sweater-B2.png`

## 采样
steps 28 / cfg 5.3 / euler_ancestral / normal

## 外观要点
- 程雾：肩上短灰蓝ボブ、黑项圈银环、青绿船领；禁止马尾发髻
- 毛衣女：披肩长直黑发、红方夹、米色高领麻花毛衣；禁止短发/项圈/青绿

## 已知残留（可接受）
程雾偶发发长漂移；脸差好于双胞胎轮，靠发型服装区分。
