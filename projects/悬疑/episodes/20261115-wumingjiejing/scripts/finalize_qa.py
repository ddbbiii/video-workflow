import json
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

episode = Path(__file__).resolve().parents[1]
repo = episode.parents[3]
image = episode / "image"
manifest_path = image / "manifest.json"
plan_path = episode / "storyboard" / "SHOT_PLAN.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
plan = json.loads(plan_path.read_text(encoding="utf-8"))
shots = plan["shots"]
records = manifest.get("shots", {})
generated = []
missing = []
failed = []
for shot in shots:
    sid = shot["id"]
    rec = records.get(sid)
    if not rec or not rec.get("file") or not (image / rec["file"]).exists():
        missing.append(sid)
    elif rec.get("pass"):
        generated.append(rec)
    else:
        failed.append(rec)

# Create a full-plan contact sheet with explicit placeholders for images not yet produced.
subprocess.run([sys.executable, str(episode / "scripts" / "run_stills.py"), "--rebuild-sheet", "all"],
               cwd=repo, check=True)
channels = Counter(rec.get("channel", "unknown") for rec in records.values())
fails_by_reason = Counter(reason for rec in failed for reason in rec.get("qa", []))
policy = json.loads((repo / "shared" / "image-api" / "channel-policy.json").read_text(encoding="utf-8"))
prices = {name: cfg.get("price_cny", 0) or 0 for name, cfg in policy["channels"].items()}
request_counts = Counter()
for rec in records.values():
    for attempt in rec.get("background_attempts", []):
        request_counts[attempt.get("channel", rec.get("channel", "unknown"))] += 1
    for attempt in rec.get("final_attempts", []):
        request_counts[attempt.get("channel", rec.get("channel", "unknown"))] += 1
anchor_file = image / "anchors" / "linxu-turnsheet-v2.png"
if anchor_file.exists():
    anchor_channel = "new2"
    (image / "anchors" / "manifest.json").write_text(json.dumps({
        "character_id": plan["character"]["character_id"],
        "channel": anchor_channel,
        "policy": manifest.get("channel_policy"),
        "model": policy["channels"][anchor_channel]["model"],
        "size": "1672x941",
        "files": ["image/anchors/linxu-turnsheet.png", "image/anchors/linxu-turnsheet-v2.png"],
        "active_file": "image/anchors/linxu-turnsheet-v2.png",
        "views": ["image/anchors/front-v2.png", "image/anchors/side-v2.png",
                  "image/anchors/back-v2.png", "image/anchors/face-v2.png"],
        "api_responses": ["image/stills-raw/linxu-turnsheet-a1-response.json",
                          "image/stills-raw/linxu-turnsheet-v2-a1-response.json"],
        "review": "v2 selected for pilot; v1 retained for comparison. See pilot6-contact and REPORT.md."
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    request_counts[anchor_channel] += 2
cost = sum(prices.get(name, 0) * count for name, count in request_counts.items())
summary = {
    "episode": episode.name,
    "generated_at": datetime.now().isoformat(timespec="seconds"),
    "policy": manifest.get("channel_policy"),
    "channels": dict(channels),
    "api_requests_by_channel": dict(request_counts),
    "api_request_total": sum(request_counts.values()),
    "planned": len(shots),
    "generated_and_passed": len(generated),
    "generated_but_failed_gate": len(failed),
    "missing": len(missing),
    "failed_shots": [{"id": r["id"], "channel": r["channel"], "dims": r["dims"],
                       "qa": r["qa"], "metrics": r["metrics"], "file": r["file"]} for r in failed],
    "missing_shots": missing,
    "contact_sheet": "image/qa/full-contact.png",
    "pilot": json.loads((image / "qa" / "pilot6-report.json").read_text(encoding="utf-8")),
    "batch_1": json.loads((image / "qa" / "batch-s02-s24-report.json").read_text(encoding="utf-8")),
    "image_api_cost_estimate_cny": round(cost, 3),
    "notes": [
        "Only pilot6 received visual review in-session; remaining stills were checked by dimensions and image metrics only.",
        "Failed and missing shots are retained/listed; no further image calls were made after batch 1.",
        "Exact map UI, labels, numbers and timing must be composed deterministically in post.",
        "The current master contact sheet has explicit NOT GENERATED tiles for missing shots."
    ]
}
(image / "qa" / "FINAL_QA.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
lines = [
    "# 《无名捷径》静帧批次 QA",
    "",
    f"- 生成时间：{summary['generated_at']}",
    f"- 通道策略：`{summary['policy']}`；静帧按通道镜头数：`{dict(channels)}`；API 请求数：`{dict(request_counts)}`",
    f"- 计划：{len(shots)} 镜；已生成 `{len(records)}` 镜；像素门禁通过 `{len(generated)}` 镜；未通过 `{len(failed)}` 镜；未生成 `{len(missing)}` 镜",
    f"- 联系表：`image/qa/full-contact.png`（未生成镜头以 NOT GENERATED 标出）",
    "",
    "## 未通过门禁",
    "",
]
if failed:
    for rec in failed:
        lines.append(f"- `{rec['id']}` / `{rec['channel']}` / {rec['dims']}：{'; '.join(rec['qa'])}；metrics={rec['metrics']}；文件 `{rec['file']}`")
else:
    lines.append("- 无")
lines += ["", "## 未生成镜头", ""]
lines.append(", ".join(f"`{sid}`" for sid in missing) if missing else "- 无")
lines += ["", "## 验收说明", "",
          "- pilot6：6/6 像素门禁通过，已人工检查锚点/小样的画风与人物一致性。",
          "- 其余镜头只做尺寸、亮度、原生锐度与 1080p 交付锐度检查；完整联系表尚待整体人工复核。",
          "- 未通过镜头和未生成镜头均保留原状态；没有重抽失败镜，也没有新增其余批次图片。",
          "- 地图、时间、门禁等 UI 文字需在后期确定性合成，不能使用模型画出的文字。",
          f"- 已完成 {sum(request_counts.values())} 次 API 请求，按各通道标价估算约 ¥{cost:.3f}；实际以通道扣费为准。",
          ""]
(image / "qa" / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
print(json.dumps({k: summary[k] for k in
                  ("planned", "generated_and_passed", "generated_but_failed_gate", "missing", "channels",
                   "failed_shots", "missing_shots", "contact_sheet")}, ensure_ascii=False, indent=2))
