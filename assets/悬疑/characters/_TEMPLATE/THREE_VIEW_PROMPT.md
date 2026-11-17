# 三视图提示词模板（2×2 拼版精简档）

> 配合 `rules/悬疑/visual.md` §六 6.0 使用。默认**一次生成 2×2 拼版**，再裁格；不分别出四张。
> 目标：一次调用拿到正/侧/背/面部四格，裁出 `front/side/back/face`。

## 统一风格前缀（固定）

```text
cinematic desaturated comic-panel space, mature simplified cel-shaded anime characters,
cold grey-blue palette, plain dark grey background, clean lineart, flat cel shading,
legible details, 16:9, no text, no watermark, no UI, no gore
```

## 布局与四格文案

```text
2x2 character turnaround sheet, four equal panels, same character in all four panels,
same scale, same outfit, same hairstyle, neutral standing pose, plain dark grey background.

Top-left: full body front view, standing straight, arms relaxed at sides.
Top-right: full body side view, 90 degrees, standing straight, arms relaxed.
Bottom-left: full body back view, standing straight, arms relaxed.
Bottom-right: front-facing head-and-shoulders portrait, flat even lighting, neutral expression.

Character: <age>岁中国<gender>，<height/build>，<hair length/color/part>，
<face shape/eyes/brows/nose/lips>，<clothing head-to-toe including collar/cuffs>，
<shoes>，<accessories>，<distinguishing marks>.
```

- 四格必须同一张脸、同一发型、同一服装、同一体型；不要四格各换一套衣服。
- 不要把“三视图”三个字当布局说明丢给模型；要写清每格的角度与景别。
- 不要求模型画编号、边框、文字；裁格由本地完成。

## 负面词

```text
photorealistic, 3D render, chibi, big eyes, child proportions (unless the character is a child),
extra limbs, deformed hands, different outfits across panels, different hairstyles across panels,
different faces across panels, half body in the three full-body panels, cropped feet,
text, labels, frame lines, watermark, UI, busy background, dramatic lighting, gore
```

## 生成顺序

1. 一次生成 2×2 拼版，存 `three-view.png`；
2. 按 2×2 裁格（内缩 3–4 px），存 `front.png` / `side.png` / `back.png` / `face.png`；
3. 逐格检查；只补坏掉的那一格（用 `front.png` 做参考），不整版重抽；
4. 整版最多重抽 2 次，单格补图最多 2 次；超限改用裁切/局部修/换表现方式；
5. 把结果与“禁止漂移项”记入 `CHARACTER_SPEC.md` 的核对记录。

## 一致性检查（四格并排看）

- 脸型、眼型、眉形、鼻梁、唇形是否同一人；
- 发际线、发长、分缝、鬓角是否一致；
- 身高比例、肩宽、体型是否一致；
- 服装主色、领口、袖口、口袋、拉链、纽扣是否一致；
- 鞋、配饰、痣/疤是否一致；
- 四格是否同一画风、同一光照、同一背景。
