# -*- coding: utf-8 -*-
"""Build a unified read-only voice asset index across UA registry + Transfer Station assets."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"E:\program\1project\video\shared\project-tools")
UA_REG = ROOT / "production/voice-library/voice-anchor-registry-v1.json"
TS_REG_MD = ROOT / "production/series/transfer-station/voice-assets/TRANSFER_STATION_VOICE_ASSET_REGISTRY.md"
TS_APPROVED = ROOT / "production/series/transfer-station/voice-assets/approved"
OUT = ROOT / "production/voice-library/VOICE-INDEX.json"
DRAFT_CHENGWU = ROOT / "production/voice-library/candidates/chengwu-anime-inner-v0/DRAFT-anchor-VA-CHENGWU-ANIME-INNER-V0.json"


def exists(path) -> bool:
    return bool(path) and Path(path).exists()


def main() -> None:
    entries = []

    if UA_REG.exists():
        data = json.loads(UA_REG.read_text(encoding="utf-8"))
        for a in data.get("anchors", []):
            audio = a.get("audio_path") or (a.get("reference_audio") or {}).get("path")
            entries.append({
                "id": a.get("id"),
                "source": "ua-anchor-registry-v1",
                "status": a.get("status"),
                "display_name": a.get("display_name"),
                "reuse_scope": a.get("reuse_scope") or a.get("approval_scope"),
                "roles": a.get("intended_roles") or [],
                "audio_path": audio,
                "audio_exists": exists(audio),
                "sha256": a.get("sha256") or (a.get("reference_audio") or {}).get("sha256"),
                "engine_contract": (a.get("clone_contract") or {}).get("engine"),
            })

    if TS_APPROVED.exists():
        for asset_dir in sorted(TS_APPROVED.iterdir()):
            if not asset_dir.is_dir():
                continue
            versions = [p for p in asset_dir.iterdir() if p.is_dir()]
            for ver in versions:
                wavs = list(ver.glob("*.wav"))
                entries.append({
                    "id": asset_dir.name,
                    "source": "transfer-station-voice-assets",
                    "status": "approved",
                    "display_name": asset_dir.name,
                    "reuse_scope": "transfer-station",
                    "roles": ["transfer-station narrator"],
                    "version_path": str(ver),
                    "audio_path": str(wavs[0]) if wavs else None,
                    "audio_exists": bool(wavs),
                    "registry_md": str(TS_REG_MD) if TS_REG_MD.exists() else None,
                    "note": "Separate schema from UA registry; do not silently reuse for Chengwu.",
                })

    if DRAFT_CHENGWU.exists():
        d = json.loads(DRAFT_CHENGWU.read_text(encoding="utf-8"))
        entries.append({
            "id": d.get("id"),
            "source": "chengwu-draft",
            "status": d.get("status") or "draft-pending-reference",
            "display_name": d.get("display_name"),
            "reuse_scope": d.get("reuse_scope"),
            "roles": d.get("intended_roles") or [],
            "audio_path": (d.get("reference_audio") or {}).get("path"),
            "audio_exists": False,
            "incoming_folder": (d.get("reference_audio") or {}).get("incoming_folder"),
            "must_not_reuse": d.get("must_not_reuse") or [],
        })

    index = {
        "schema": "voice-index-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "authoritative_delivery_engine": "Qwen3-TTS-12Hz-1.7B-Base",
        "ua_registry": str(UA_REG),
        "count": len(entries),
        "entries": entries,
        "notes": [
            "Read-only index for assistants and humans.",
            "Delivery must use approved UA-style Base-clone anchors (or newly approved ones).",
            "Transfer Station assets keep their own approval trail.",
            "Chengwu draft is not usable until reference WAV + approval.",
        ],
    }
    OUT.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(OUT), "count": len(entries)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
