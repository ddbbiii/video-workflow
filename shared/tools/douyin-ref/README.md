# 抖音参考片获取（工具目录）

- 规则真源：`rules/shared/douyin-reference.md`
- 用法：`python shared/tools/douyin-ref/fetch_ref.py "<抖音链接>" --out work/refs/<YYYYMMDD> --overwrite`
- 依赖独立仓库 `../douyin-media-mcp/`（相对于 video 仓库根目录；也可用 `DOUYIN_MCP_ROOT` 指定其他位置）；浏览器解析必须完全访问权限。
- 输出：视频 + `<视频>.manifest.json`（时长、分辨率、sha256、候选理由；不含 Cookie/签名 URL）。
- 只作内部参考拆解，不二次分发、不进成品、不切片当素材。
