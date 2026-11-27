# 共用能力

本机 GPU 统一排队入口见 [gpu-queue/README.md](gpu-queue/README.md)。各助手提交请求并通知 GPU 管理聊天，获准后执行。

这里保存四条线路都能复用的图片 API、网格分镜、音频、字幕、合成、封面和资产注册表。

线路专属规则、角色、声线和单集资产必须留在线路目录。

通用静帧推拉平移工具见 [camera-motion/README.md](camera-motion/README.md)。渲染引擎与主题配置分离，当前提供浮点仿射后端、参数预检、逐镜恢复及运动质量检查。

各助手共用的运镜原则见 [camera-motion/MOTION_GUIDELINES.md](camera-motion/MOTION_GUIDELINES.md)：affine 默认、运动清晰可感知、柔和起停、主体保护；具体数值仅供参考，主题节奏按线路规则执行。

剪映本地草稿迁移到 WeftCut 的已验证流程与当前工程交接见 [workflows/weftcut/README.md](workflows/weftcut/README.md)。
