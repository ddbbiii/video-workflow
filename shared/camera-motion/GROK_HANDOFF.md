# Grok 交接：通用静帧运镜 Blender 后端

日期：2026-10-06。此文档用于交接，不表示已向 Grok 发送任务。用户批准研究和实现新的通用方案；本任务不涉及付费生图或视频 API。

## 目标

为现有通用静帧运镜工具增加可选 Blender 后端，仅支持单图片正交相机的推近、拉远、横移、纵移及组合运动。跨项目、跨主题、横竖屏共用。用同一素材、同一轨迹与 affine 后端比较，不能默认 Blender 更好。

交付最小可运行后端、安装/运行说明、配置示例、测试、真实质量和性能对照。暂不做分层视差、遮挡补图、内部动画、景深、运动模糊、超分、插帧、音乐或配音。

## 现状与入口

工作区：`E:\program\1project\video`，Windows PowerShell。

- `shared/camera-motion/camera_motion.py`：参数校验、轨迹、RGB 浮点 affine 渲染、FFmpeg 编码、逐镜恢复、总览。
- `shared/camera-motion/verify_motion.py`：编码后连续帧 ECC 对比预期运动，低纹理/失败标不确定。
- `shared/camera-motion/test_camera_motion.py`：曲线、亚像素、画幅/边界、横竖屏、不同长度、恢复测试。
- `shared/camera-motion/README.md`：当前使用与限制。
- 助眠线曾用于验证通用镜头接入；原始示例配置不在当前仓库中。
- 同集 `gen_rebuild/runs/20261006-032431-batch02-landscape/video_generic_v1/`：5段基准视频、总览、trajectory、qa。

目前 Python、OpenCV、NumPy、Pillow、FFmpeg/ffprobe 可用。之前 PATH 中未找到 Blender；实现前重新检查本机安装，不假设存在。没有 Git 仓库可依赖，不执行 git reset/checkout 或清理旧资产。

## 配置契约

保持 `schema_version:1`，新增 `backend:"blender"`。原 `backend:"affine"` 必须继续可用，未知或缺失运行环境不得静默回退。

全局 `output:{width,height,fps}`；`shots` 支持不同 `duration_s`；可选 `overview`、`transition_s`。图片 `source` 相对配置文件解析。

每镜字段：`id`、`source`、`duration_s`、`start_view`、`end_view`、`curve`、可选 `required_regions`。

取景框 `[x,y,w,h]` 是 EXIF 校正后的原图归一化坐标，左上原点，x 向右、y 向下。框宽高必须符合输出画幅，禁止拉伸。轨迹在取景框空间插值，不能改成插值 zoom 值导致运动不一致。保护区域必须完整留在画面。

曲线支持 linear、smoothstep、ramped_linear（ramp_s）。必须复用或提取现有 `progress`、`view_at` 的定义，不独立近似。N=duration*fps，帧 i 时间为 i/fps，首尾跨越 `(N-1)/fps`。第0帧精确起点，第N-1帧精确终点，不额外复制首尾帧。

举例：

```json
{
  "schema_version": 1,
  "backend": "blender",
  "output": {"width": 1920, "height": 1080, "fps": 30},
  "overview": false,
  "shots": [{
    "id": "pan",
    "source": "texture.png",
    "duration_s": 9,
    "start_view": [0.006, 0.012, 0.976, 0.976],
    "end_view": [0.018, 0.012, 0.976, 0.976],
    "curve": {"type": "ramped_linear", "ramp_s": 0.75}
  }]
}
```

## Blender 实现要求

1. 独立 `blender_backend.py` 与无界面场景脚本，入口调用 `blender --background ...`，不能依赖 UI、用户默认场景或手动点击。
2. 使用正交相机＋原图纹理平面；按原图宽高比建平面。明确 UV/图像上下方向、相机取景比例、像素中心约定。不要把 `ortho_scale` 的宽高含义想当然，需用棋盘格实测。
3. 每帧从统一轨迹设置相机，不使用 Blender 自动 Bezier 插值偷偷改变速度。可以把轨迹预先导出，Blender 端逐帧消费，避免其 Python 环境依赖主 Python 的 cv2。
4. 无光照干扰的图片材质，关闭不必要阴影/辉光/景深/抖动采样/动态曝光。核实色彩管理，不让 AgX 或其他调色把输入图整体变亮变暗；材质与输出设置要随支持版本验证。
5. 采样、纹理过滤和渲染引擎选择通过实际硬边/细纹理对照确定，记录参数。首轮关闭 motion blur，避免用模糊掩盖抖动。
6. 优先无损帧序列，经现有 FFmpeg 同参数编码。帧缓存单独保存，支持按运行清单恢复；不要无授权删除缓存或旧输出。
7. 明确支持和实际测试的 Blender 版本，提供可配置可执行文件路径。若需下载，使用官方发行，不写全局 PATH、不改系统默认设置、不在源代码嵌入机器专属路径。
8. 可提取共用轨迹/校验模块，但保持现有 CLI 兼容、默认 affine 不变。安装/实现失败明确报错。

## 验收矩阵

必须包含横屏和竖屏；同画幅与跨画幅显式裁切；短镜与较长镜；推、拉、横移、纵移、组合运动；linear 与 ramped_linear。测试材料覆盖棋盘硬边、小字、星点、岩层细纹理和照片。合成测试素材可本地生成，不调用图片 API。

- 比较双方完全相同的原图、取景轨迹、时长、fps、分辨率、编码参数。不能通过降低细节、改成不同速度或加运动模糊宣称更稳定。
- 用棋盘/位置标记核对起止画面、方向、缩放、UV和像素中心。
- 完整解码、帧数/尺寸/fps、音轨（本任务无音轨）、时长检查。
- 保留 `*-trajectory.json` 的 `inverse_sample_matrices` 契约：输出像素到实际坐标系的取样矩阵；必须声明坐标系，并使验收器可推导正确的相邻帧画面变换 `inv(P_next) @ P_current`。
- ECC 在同一 ROI 测速度残差，转换裁剪坐标，不直接比较局部平移项与全局平移项。现有默认残差阈值0.08像素、ECC相关度0.98，仅是局部数值检查，不能宣称肉眼完全无抖动。
- 检查细纹理闪烁/模糊、静止区亮度和颜色漂移；报告测量方法和不确定性。
- 记录初始化耗时、总渲染耗时、平均帧耗时、内存/显存观察、输出体积与软硬件版本。
- 输出可播放 old/affine 与 Blender 对比，位置标明，说明实际播放验收仍待用户确认。

如果质量收益很小但成本显著增加，允许推荐保留 affine 默认、Blender 可选。任务成功标准是可审阅证据，不是强行迁移。

## 交付与协作边界

- 交付代码、依赖/安装说明、测试命令、测试配置、运行 manifest、QA报告、比较视频路径、剩余问题。
- 修改限于 `shared/camera-motion/`，真实测试配置留项目中，运行资产写新目录。不改最高工作流、声线、文案、旧图和原配音。
- 手动编辑使用 apply_patch。不得回显密钥，不读取无关凭据，本任务无需 API key。
- 多图检查使用隔离图片任务和低清联系表；不向长期主线程返回图片/base64载荷，只返回文字和绝对路径。
- 不发消息给其他会话或外部人员；不发布、不上传私有素材。
- 若只能离线交付代码而无法在本机验证，明确标为“未验证候选”，不要伪造通过记录。

## 开源资料

- Blender 相机：https://docs.blender.org/manual/en/latest/render/cameras.html
- Blender Python API：https://docs.blender.org/api/current/
- Blender 代码与许可证：https://github.com/blender/blender
- MLT affine：https://www.mltframework.org/plugins/FilterAffine/
- OpenCV 几何变换：https://docs.opencv.org/4.x/da/d54/group__imgproc__transform.html

优先利用成熟 API、相机/纹理/采样能力。借鉴设计和复制代码要区分；若复制第三方源码，须记录来源版本、适用许可证和必要声明。无需引入 Remotion 或 MoviePy 作为额外依赖。
