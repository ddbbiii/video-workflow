# 小球线视频产出规范

本文件规定小球线单集如何被 Motion Studio 识别、导入、预览和导出。Studio 与单集工程必须遵循同一份机器可读清单；不得依靠文件名猜测项目类型、输出规格或参数含义。

## 单集入口

可导入的单集源目录必须包含：

```text
<episode>/
  studio/episode.json
  simulation/trace.json
```

`studio/episode.json` 是本规范的机器可读真源。Studio 校验 `schema_version`、`episode_id`、`model_id`、轨迹路径、轨迹结构和输出设置；不支持或缺失必需字段时，导入必须失败并指出字段，不得静默回退到另一集的配置。Markdown 用于维护和审核规则，不由 Studio 解析。

## 清单字段

- `schema_version`：正整数；当前只接受 `1`。
- `episode_id`：稳定单集标识，须与轨迹及 Studio 当前支持的适配器一致。
- `episode_name`：界面显示名称。
- `model_id`：物理/渲染适配器标识；当前 Motion Studio 安装了 `matter-ring-escape-v1`。
- `adapter_version`：正整数适配器版本；必须与 Studio 已安装运行时完全匹配。适配器由 Motion Studio 管理，不随单集复制。
- `simulation.trace`：相对单集目录的 JSON 轨迹路径；不得包含绝对路径或 `..`。
- `simulation.seed`：生成该轨迹的确定性随机种子。预览和导出必须读取同一份预生成轨迹，不得各自重新抽样。
- `simulation.fps`：轨迹采样帧率，正整数；与轨迹中的 `fps` 相等。
- `output.width`、`output.height`：正整数像素尺寸；当前竖屏默认 1080×1920。
- `output.fps`：建议成片帧率，正整数；默认 60 fps。Studio 可在高级输出设置中覆盖。
- `output.frame_count`：本期建议总帧数，正整数；Studio 可手动覆盖。时长由 `frame_count / fps` 得出。
- `output.minimum_frames`、`output.maximum_frames`：本期可接受的帧数区间；越界必须明确报错，不得静默截断。
- `output.quality`：编码质量档位；当前接受 `high`，映射为 H.264 `libx264`、CRF 18、`yuv420p`。
- `output.frame_count_policy`：单集处理帧数覆盖的方法；当前适配器接受 `trim-or-hold`，短于轨迹时裁切，长于轨迹时保持轨迹终态。更复杂的结尾须由单集渲染器实现并声明自己的策略。
- `parameters`：本集参数默认值，字段及类型必须匹配对应适配器定义。
- `asset_limit_bytes`：单项导入素材大小上限，正整数。

## 帧率、轨迹与稳定性

轨迹可用较低采样帧率保存；渲染时必须按时间对相邻状态插值到输出帧率。碰撞及其他事件按轨迹时间映射到输出时间，不能因帧率换算或回放速度而漏掉、提前或错位。首帧必须对应轨迹第 0 帧；碰撞脉冲只允许在事件发生后生效。随机种子和轨迹在生成预览前确定并持久化，导出复用该轨迹。

单集可实现自己的结束条件和可选结束动画。Studio 只传递经校验的输出帧数、帧率、尺寸和质量档位，并检查最终文件属性；Studio 不推断单集的剧情结束方式。若帧数策略超出适配器能力，适配器须在渲染前返回可读错误。

## 参数与项目文件

项目参数写入源目录 `studio/project.json`；素材存入 `studio/assets/`，预览成片存入 `studio/previews/`。项目文件包含清单版本、单集标识、适配器标识、用户参数、输出覆盖值、随机种子和素材相对路径。不得把可迁移项目的唯一副本只保存在操作系统应用数据目录。

数值参数必须是有限数字并符合其物理/文件格式约束。滑杆用于快速调节，数值框支持精确输入。非法值必须显示错误且不得悄悄改写。速度和球体显示尺寸不使用狭窄的任意滑杆边界；速度须为正数，球体尺寸须为正数且不能造成不可渲染图形。

## 导出验收

导出前检查清单兼容性、轨迹帧率与结构、输出参数区间、引用素材存在性。导出后以实际文件探测结果核对编码、宽高、帧率、帧数、时长和完整解码；验收值来自本次项目输出设置，不得硬编码为 30 fps、360 帧或 12 秒。

当前十重圆环清单示例：`episodes/20261122-escape-rings/studio/episode.json`。Motion Studio 独立项目及版本见线路入口 README 的软件索引记录。
