# 《鳌太线凌晨进山》角色锁 v2

## 全局主角

`catman` 只引用人生体验线全局资产：

- `assets/人生体验/characters/catman-20261113/character-reference/turnaround.png`
- `assets/人生体验/characters/catman-20261113/character-reference/face-style-D.png`
- `assets/人生体验/characters/catman-20261113/character-reference/expressions/`

本集的猫头人是第二人称“你”的视觉化身，计入五名队员之一，不是旁观者、讲解员或第六个人。只允许增加本集状态：深色冬季外层、无品牌小型登山包、雾雪和疲劳；不得改变猫脸、折耳、头身比例、猫爪、赤脚和无尾巴。

## 本集配角

队友和救援人员都使用同一套二维平涂的简笔圆头人，不画写实五官、真人皮肤、分指手或电影写实身体。

| ID | 用途 | 参考 |
|---|---|---|
| `helper-a` | 领队/队友 | `character-reference/ref-helper-a.png` |
| `helper-b` | 回撤队友 | `character-reference/ref-helper-b.png` |
| `helper-c` | 继续前行队友 | `character-reference/ref-helper-c.png` |
| `helper-d` | 继续前行队友 | `character-reference/ref-helper-d.png` |
| `rescue-worker` | 搜救人员 | `character-reference/ref-rescue-worker.png` |
| `purple-woman` | 虚构传说剪影，不对应真实人物 | `character-reference/ref-purple-woman.png` |

## 镜头门禁

- `cast=none` 只能用于无人环境、道具或地形镜。
- 只要画面出现人物，`character_ids` 必须列出全部角色，生成器必须同时提交对应参考。
- 五人队伍必须包含 `catman + helper-a + helper-b + helper-c + helper-d`。
- 不允许 `body-only`、`anonymous hikers`、`neutral trail tokens` 或未登记人物作为生产角色。
- 紫衣女人只能作为无脸、不可识别的紫色虚构剪影出现，不得画成真实女性或具体受害者。
