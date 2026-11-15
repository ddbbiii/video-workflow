# 2026-11-16 清理清单

本轮只处理已完成引用核查的对象。清理前 checkpoint 为本次规则整理提交；其他工作区改动不纳入提交。

## 已清理

| 路径 | 原因 | 保留依据 | 预计释放 |
|---|---|---|---:|
| `projects/助眠解说/episodes/catching-a-second/runs/20261112-cas-b01/intro/` | 纯正文交付后废止的旧片头批量渲染与预览 | 当前正文、SRT、QA、manifest 不依赖该目录 | 200 个文件，507,922,869 字节（0.473 GiB） |

## 暂不删除

| 路径 | 原因 |
|---|---|
| `.../runs/20261112-cas-b01/delivery/` | `PROJECT_STATE.md`、字幕 QA 和组装脚本仍引用正式视频/音频文件 |
| `shared/image-api/runs/` 各实验目录 | 多个报告、脚本和 `channel-policy.json` 仍引用；需逐实验保留报告后再清理原图 |
| `video/final/`、`archive/`、项目归档目录 | 交付或历史恢复依据，当前无法证明已被完全替代 |

## 后续候选

- 对 `shared/image-api/runs/` 建立“报告/manifest 保留、原图按实验删除”的逐目录清单。
- 核验 `body_clips/` 与正式 `video/final/` 的哈希和恢复用途后，再决定是否清理中间片段。
- 清理任何新增对象前，先更新本清单并做精确引用核查。
