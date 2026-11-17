# Mac 工作站交接

本文面向 48 GB 统一内存的 Apple Silicon Mac，用于接手本仓库当前视频日常制作。所有仓库路径均相对于仓库根目录；`<仓库根目录>` 是本机克隆位置的占位符，不要把某台机器的绝对路径写进仓库文档。

## 结论与范围

当前常规流程可在 Mac 独立运行，不要求 NVIDIA GPU 或 CUDA：远程图片 API 生图、Python/NumPy affine 推拉平移、FFmpeg 合成、SRT 生成与 QA。48 GB 统一内存足以覆盖这类工作。Apple Silicon 上 FFmpeg 编码可用 VideoToolbox，但交付参数和 QA 仍以仓库规则为准；CPU `libx264` 是可用基线。

本交接不承诺旧的本地 CUDA 推理链（视频生成、超分、插帧、旧 TTS/口型等）可直接迁移。相关模型/运行时不随 Git 克隆；当前默认流程需要这些能力时应另行评估，不能静默替换。

## 1. 克隆与基础工具

安装 Xcode Command Line Tools、Homebrew、Git、Python 3.11、FFmpeg 和 `uv`：

```sh
xcode-select --install
brew install git git-lfs python@3.11 ffmpeg uv
git clone <视频仓库地址>
cd video
git lfs install
git lfs pull
```

确认 `python3.11`、`ffmpeg`、`ffprobe`、`uv` 均能从终端找到。不要在仓库中提交虚拟环境。

为 Python 脚本创建独立环境并安装当前主流程常用依赖：

```sh
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install numpy pillow opencv-python-headless jieba
```

仓库当前没有统一的依赖锁文件；依赖清单尚未产品化，以上为 Mac 初始环境清单。具体脚本如提示缺少模块，再按该脚本实际 import 安装，并把可复用依赖补入后续依赖文件。音频/历史归档工具可能需要额外套件，不属于当前正文视频基线。

## 2. API 凭证

图片 API 密钥只设置为当前用户环境变量或密钥管理器项目，不写进脚本、文档、shell 历史或 Git。当前活跃策略以 `shared/image-api/channel-policy.json` 为准，版本为 `v8-new2-dklb-parallel`，需要以下变量：

- `IMAGE_API_KEY_XXC`：`new2`
- `IMAGE_API_KEY_DKL`：`dkl-b`

macOS 當前終端可先這樣設置（替換佔位內容，命令不含真實密鑰）：

```sh
export IMAGE_API_KEY_XXC='<从密钥管理器取得>'
export IMAGE_API_KEY_DKL='<从密钥管理器取得>'
```

若要跨终端持久化，建议使用 macOS Keychain 并由启动脚本读取；不要直接把值写入 `.zshrc` 或本仓库。第一次批量生图前遵循流程规则核对额度并先做单张试调用。

## 3. 生图入口与 Mac 兼容性

悬疑单集入口 `projects/悬疑/episodes/<单集>/scripts/run_stills.py` 会导入 `projects/悬疑/visual-tests/20261114-pilot-8shots/gen_pilot.py`。该通用脚本现已改为只从环境变量读取 API Key，不再依赖 Windows `winreg`。

切换到新机器后先做只读语法检查，再对当前制作单集按项目状态文件中的入口运行；不要对归档项目盲目批处理：

```sh
python -m py_compile projects/悬疑/visual-tests/20261114-pilot-8shots/gen_pilot.py
python -m py_compile projects/悬疑/episodes/<单集>/scripts/run_stills.py
```

由于生图会产生费用，首次功能验收应指定单张/小样入口，并确认路由、尺寸、日志和 QA 输出正确后再跑批量。活跃策略和参数以 `channel-policy.json` 及对应线路视觉规则为准，不复制到本交接文档维护。

## 4. 合成、运镜与验收

- 静帧推拉平移使用 `shared/camera-motion/` 的 affine 后端。它依赖 NumPy、OpenCV 和 FFmpeg，可在 CPU 上运行，不依赖 CUDA。
- 在 `shared/camera-motion/` 目录运行 `python test_camera_motion.py`，可执行仓库现有的合成运镜回归测试。
- 常规视频编码使用系统 FFmpeg；核对版本和编码器：

```sh
ffmpeg -version
ffmpeg -hide_banner -encoders | rg 'libx264|h264_videotoolbox'
ffprobe -version
```

- 先执行计划校验，再按运镜 README 与单集状态文件的命令运行；最终交付前运行项目已有 QA。规格、旁白/SRT 约束与返工门禁以 `rules/shared/video-workflow.md`、`rules/shared/delivery.md`、`rules/shared/srt.md` 为真源。
- Mac 首次 smoke test 应覆盖：小图 affine 运动、短片 FFmpeg 合成、`ffprobe` 读取、SRT 校验，以及一个单张远程生图调用。记录所用 Mac/系统/FFmpeg 版本与结果到对应单集 QA 或迁移记录。

## 5. Git 同步与本地生成数据

`assets/` 的正式视觉素材通过 Git LFS 同步，`.codex-memory/` 的项目级记忆和各集 `story/`、`PROJECT_STATE.md` 等文本稿通过普通 Git 同步。每集沿用固定目录名，例如 `projects/人生体验/episodes/20261115-henshi/`。克隆后运行 `git lfs pull`，并检查 `git lfs ls-files`；仅有 LFS 指针而没有实际图片时，生图流程不能直接运行。

Git 克隆仍不会包含下列本地生成数据。迁移前先对照当前制作单集的 `PROJECT_STATE.md`、manifest 和 QA 报告，按需复制确实要继续工作的文件，并核对文件数/大小或 manifest 哈希：

- 活跃单集的 `image/`、`video/`、`qa/`、`logs/`、`drafts/`、`assets/` 等被忽略产物；这些媒体、运行缓存和混合草稿目录不随 Git 同步。需续做旧集时，按 `PROJECT_STATE.md` 单独核对缺失的原图、关键帧和片段。
- 旧音频、字体和 SDXL 模型已归档到仓库旁 `video-archive/20261117-retired-assets/`，不属于当前跨机同步范围。
- 仓库外 `video-archive/` 只在明确恢复历史流程时需要，不属于当前默认生产依赖。

以下本机大目录不要为了当前 Mac 日常流程整包复制：`shared/runtime/`、`shared/lip-tools/`、`models/`、`work/`。它们包含 Windows/CUDA 工具链、模型或临时工作数据；只有恢复对应旧工作流时才逐项评估。迁移时不删除源机器数据。

工作区还有未提交改动时，`git clone` 只能取到已推送提交。未提交源文件需要之后单独审阅并迁移/提交；不要把它们与 Git 忽略的媒体素材混为一类。

## 6. 外部工具仓库与 Codex 配置

### 抖音参考片 MCP（按需）

`douyin-media-mcp` 是仓库外独立项目，Mac 需另行 clone、建虚拟环境并安装依赖。其 Python 环境在 macOS 使用 `.venv/bin/python`；依赖 FFmpeg/ffprobe 和需要时的浏览器登录状态。工作区封装脚本默认从 `../douyin-media-mcp/` 查找，也可在当前 shell 设置 `DOUYIN_MCP_ROOT`。其 Git 状态应单独检查，不随本仓库克隆。

如需将 MCP 注册进 Codex，需在 Mac 的 Codex 用户配置中单独添加 `douyin-media` stdio server，命令使用 `uv` 和 MCP 仓库目录。Codex 用户配置是机器本地配置，注册时必须指向 Mac 实际 clone 的 MCP 路径；本交接不保存该路径或用户配置文件内容。详细契约见 `rules/shared/douyin-reference.md`。

### MCP 与 Skills

MCP/Skills 是 Codex 用户环境配置，不会随视频仓库 Git clone。迁移时在 Codex 设置中分别核对：

- 常驻/可能复用 MCP：`tieba`、`node_repl`、`xiangsu-mcp-manager`。像塑编辑器相关能力需重新连接本机像塑；不是视频基础流程依赖。
- 可选外部 MCP：`douyin-media-mcp`，仅在取参考片时使用。
- 可能相关 Skills：`memory-discipline`、`codex-image-context-hygiene`；封面需求才需要 `video-cover-poster`。旧 `sleep-aid-intro` 属于已变更/归档的片头工作流，不是当前正文制作前置条件。

以上是当前机器配置盘点，不代表所有 MCP/Skill 都已在 Mac 验证。Mac 上应重新安装/授权并逐项 smoke test；不要复制密钥、Cookie、浏览器配置数据库或 Windows 插件目录。

## 7. 已知待验证项与交接完成标准

- 本文和关键入口已修复 Windows 注册表依赖，但尚未在 Apple Silicon Mac 实机跑通；`py_compile` 只验证语法，不能替代 API/FFmpeg 实测。
- 第一次生图需确认 Mac 网络、代理、API 凭证和两个有效通道均正常；不要打印或提交密钥。
- 至少用一个活跃单集验证：资产读取、单张生图、affine 小样、FFmpeg 编码、SRT/QA。核对素材迁移完整后再将 Mac 设为主要工作站。
- 推拉镜视频或任何本地模型推理如果重新进入计划，单独核对 Apple Silicon/MPS/Metal 支持、速度和质量；不得把 CUDA 可用性假定为 Metal 等价。

## 参考入口

- 工作区全局规则：`rules/shared/README.md`
- 固定制作流程：`rules/shared/video-workflow.md`
- 交付与 SRT：`rules/shared/delivery.md`、`rules/shared/srt.md`
- 图片 API：`shared/image-api/README.md`、`shared/image-api/channel-policy.json`
- affine 运镜：`shared/camera-motion/README.md`、`shared/camera-motion/MOTION_GUIDELINES.md`
- 抖音参考片：`rules/shared/douyin-reference.md`
- Git 忽略约定：`.gitignore`
