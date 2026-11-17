# GPU 统一排队

2026-10-06 用户指定本聊天统一管理 GPU 使用。

- 管理聊天：`01a10e62-835a-78b2-8c7b-6d79e97ce195`。
- 共享队列目录：`shared/gpu-queue/`（相对于仓库根目录）。
- 其他助手将请求写入 `requests/<唯一任务ID>.json`，不要在提交请求时启动 GPU 工作。写入请求即进入统一调度，不需要所属会话逐项催办或重复确认。
- 调度顺序：显式 `priority` 越高越优先；未填写 `priority` 时按 `submitted_at` 先到先执行。同一优先级按提交时间稳定排序。一次只放行一个 GPU 重任务，等待中的任务可继续 CPU 准备工作。
- 管理助手自动检查资源、锁和前序任务，写入 `granted` 后直接安排执行，不发送普通过程通知；执行助手写入 `running`、PID、日志路径，完成后写入 `completed` 或 `failed`。
- 通知策略：任务排队、获准、启动和运行中的普通状态不通知所属会话；任务完成、失败、取消，或遇到必须由所属会话决定的任务信息变更时，才主动通知对应会话。所属会话主动修改任务信息时，按新信息重新调度。
- 请求状态：`queued -> granted -> running -> completed/failed`；取消写入 `cancelled`。仅管理助手授予名额；仅提交者更新自己任务的运行结果。
- GPU 范围包含本地 I2V、生图、超分、GPU TTS、Blender GPU 渲染等。远程图片 API 和纯 CPU 任务无需占本机 GPU 名额。
- 继续遵循现有 GPU 锁协议。主锁路径为 `shared/work/cache/gpu.lock`；`shared/runtime/comfy/cache/gpu.lock` 是需额外检查的旧路径保护。队列许可不能绕过正在运行的任务或锁，不能根据一次空闲采样删除锁。
- ComfyUI 的队列只涵盖本实例，不能代表整机空闲。放行前检查 GPU 进程、现有锁以及 8188/8189 队列；批次脚本可能在两次提交间暂时显示空队列。
- 本目录是共享调度记录，由管理聊天处理。写入请求后通知管理聊天；管理助手主动核对完成和进程退出并接续下一项，不等待用户催促。终态漏更新时可依据 manifest、完成日志、进程退出和服务队列记录修正调度状态；视觉 QA 和正文批准仍由所属线路处理。
- 请求不得包含密钥；正式生产授权和线路内容审批仍按现有规则执行。

- 空队列时立即暂停定时任务 `gpu`，不持续轮询；存在 queued/granted/running 请求时轮询间隔为十五分钟。第一条新请求入队后，提交助手必须通过聊天工具通知管理聊天 `01a10e62-835a-78b2-8c7b-6d79e97ce195`（含请求 ID/路径）；管理聊天收到后立即调度，并用 automation_update 将 `gpu` 恢复 ACTIVE、保留十五分钟间隔。只写请求文件不会唤醒已暂停的定时任务。

请求格式示例（复制后填写真实值）：

```json
{
  "id": "line-task-unique-id",
  "owner_thread": "提交助手的聊天ID",
  "line": "线路名",
  "submitted_at": "2026-10-06T00:00:00+08:00",
  "priority": null,
  "status": "queued",
  "task": "任务说明",
  "command_or_workflow_path": "绝对路径或明确执行入口",
  "working_directory": "绝对路径",
  "output_directory": "绝对路径",
  "estimated_minutes": null,
  "estimated_vram_mb": null,
  "dependencies": [],
  "authorization": "已获用户授权的范围",
  "pid": null,
  "log_path": null
}
```

运行情况见 `STATE.md`；具体请求文件为任务状态依据。
