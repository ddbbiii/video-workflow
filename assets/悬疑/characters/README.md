# 悬疑角色资产

> 规则真源：`rules/悬疑/visual.md` §六（2026-11-08 强化；同日二次收窄为 2×2 拼版精简档）。
> 2026-11-08 建目录。此前没有正式角色资产：首集只有单张半身锚点，没有三视图。

## 目录

```text
<character_id>/
  three-view.png      # 2×2 拼版原图（正/侧/背/面部四格）
  front.png           # 正面全身（裁格）
  side.png            # 侧面 90°（裁格）
  back.png            # 背面（裁格）
  face.png            # 面部特写（裁格/放大）
  expressions/        # 可选，4 格表情
  costume/            # 可选，服装变体
  state/              # 可选：受伤、湿身、年龄变化
  CHARACTER_SPEC.md   # 固定提示词、seed、禁止漂移项、复用范围
```

## 命名与范围

- `character_id` 用小写英文/拼音短名，与 `storyboard/CHARACTER_LOCK.md`、manifest 的 `character_ids` 一致；
- 跨集复用同一角色沿用同一 id；单集专用在 spec 里写 `episode-only`；
- 换装、受伤、湿身、年龄变化建 `state/` 变体，不覆盖基础三视图。

## 弱复用（soft reuse）

- 规则见 `rules/悬疑/visual.md` §六 6.6：硬条件 4 条全过 + 软条件 ≥3/4 才复用，不强行让每集共用一张脸；
- 默认**同脸复用**：同一套脸演新姓名/新身份，不是同一人；同人复用（同一身份连续）只用于续集；同一张脸不得同集出现两个角色；
- 复用集不新建三视图，只按需做 1 张 `state/` 或 `costume/` 变体（0–2 次）；在 `CHARACTER_SPEC.md` 的 `reuse-mode` / `portrayed-as` / `reused-in` 记录；
- 首个新建主角建成后标 `series-reusable` 候选；后续每单先判契合度，再决定复用或新建。

## 现状（2026-11-08 审计）

- 《病历对不上》周砚 / 林晚 / 小满：只有 `projects/悬疑/episodes/20261107-bingli/image/anchor/` 的单张半身 3/4 锚点，**未建三视图，未迁入本目录**；
- 新单按 `visual.md` §六：先出主角 1 张 2×2 拼版三视图并锁定，再批量生图；配角 B 档只建 1 张正面/3-4 参考；
- 本节生效前已完成的单集不自动返工；补做需用户点名。

## 模板

复制 `_TEMPLATE/CHARACTER_SPEC.md` 到 `<character_id>/CHARACTER_SPEC.md` 后填写；
三视图提示词用 `_TEMPLATE/THREE_VIEW_PROMPT.md`；
每集批量前把 `_TEMPLATE/CHARACTER_LOCK.md` 复制到该集 `storyboard/CHARACTER_LOCK.md`；
新单先查 `REUSE_POOL.md`，再填 `_TEMPLATE/REUSE_FIT_CHECK.md`，通过契合度表才复用。
