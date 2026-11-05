# -*- coding: utf-8 -*-
"""One-shot: copy approved legacy anchors into voice-v3 library + registry."""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"E:\program\1project\video\shared\project-tools")
V3 = ROOT / "production" / "voice-v3"
REG = V3 / "registry" / "anchors.json"
LIB = V3 / "library" / "anchors"
DRAFTS = V3 / "library" / "drafts"
OLD_REG = ROOT / "production" / "voice-library" / "voice-anchor-registry-v1.json"
TS_APPROVED = ROOT / "production" / "series" / "transfer-station" / "voice-assets" / "approved"
CHENGWU_DRAFT = ROOT / "production" / "voice-library" / "candidates" / "chengwu-anime-inner-v0"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest().upper()


def copy_anchor(anchor_id: str, wav: Path, transcript: str, meta: dict) -> dict:
    dest = LIB / anchor_id
    dest.mkdir(parents=True, exist_ok=True)
    ref_wav = dest / "reference.wav"
    ref_txt = dest / "reference.txt"
    if not ref_wav.exists() or sha256_file(ref_wav) != sha256_file(wav):
        shutil.copy2(wav, ref_wav)
    ref_txt.write_text(transcript.strip() + "\n", encoding="utf-8")
    digest = sha256_file(ref_wav)
    entry = {
        "id": anchor_id,
        "status": "approved",
        "display_name": meta.get("display_name") or anchor_id,
        "project": meta.get("project") or "legacy",
        "roles": meta.get("roles") or [],
        "reuse_scope": meta.get("reuse_scope") or "restricted",
        "reference_wav": str(ref_wav),
        "reference_txt": str(ref_txt),
        "sha256": digest,
        "engine": "Qwen3-TTS-12Hz-1.7B-Base",
        "transcript": transcript.strip(),
        "migrated_from": meta.get("migrated_from"),
        "migrated_at": datetime.now(timezone.utc).isoformat(),
        "rights": meta.get("rights") or {"clone_consent": "approved-legacy"},
    }
    (dest / "meta.json").write_text(json.dumps(entry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return entry


def main() -> None:
    LIB.mkdir(parents=True, exist_ok=True)
    DRAFTS.mkdir(parents=True, exist_ok=True)
    (V3 / "runs").mkdir(parents=True, exist_ok=True)
    anchors = []

    if OLD_REG.exists():
        old = json.loads(OLD_REG.read_text(encoding="utf-8"))
        for a in old.get("anchors", []):
            if a.get("status") != "approved":
                continue
            wav = Path(a.get("audio_path") or (a.get("reference_audio") or {}).get("path") or "")
            # normalize weird escapes
            if not wav.exists():
                wav = Path(str(wav).replace("\\\\", "\\"))
            transcript = a.get("exact_transcript") or (a.get("transcript") or {}).get("text") or ""
            if not wav.exists() or not transcript:
                print("SKIP", a.get("id"), "missing wav/transcript", wav)
                continue
            project = "urban-anomaly"
            roles = a.get("intended_roles") or []
            entry = copy_anchor(
                a["id"], wav, transcript,
                {
                    "display_name": a.get("display_name"),
                    "project": project,
                    "roles": roles,
                    "reuse_scope": a.get("reuse_scope"),
                    "migrated_from": str(OLD_REG),
                    "rights": a.get("rights") or a.get("rights_and_use"),
                },
            )
            anchors.append(entry)
            print("MIGRATE", entry["id"])

    if TS_APPROVED.exists():
        for asset in sorted(TS_APPROVED.iterdir()):
            if not asset.is_dir():
                continue
            vers = [p for p in asset.iterdir() if p.is_dir()]
            if not vers:
                continue
            ver = sorted(vers)[-1]
            wavs = list(ver.glob("*reference*.wav")) or list(ver.glob("*.wav"))
            if not wavs:
                print("SKIP TS", asset.name, "no wav")
                continue
            wav = wavs[0]
            # TS may lack exact transcript beside wav — use placeholder note file if missing
            txt_candidates = list(ver.glob("*.txt")) + list(ver.glob("*transcript*"))
            if txt_candidates:
                transcript = txt_candidates[0].read_text(encoding="utf-8", errors="replace").strip()
            else:
                transcript = f"[TRANSCRIPT PENDING FOR {asset.name}] 请补逐字稿后再作 Base clone 交付。"
            entry = copy_anchor(
                asset.name, wav, transcript,
                {
                    "display_name": asset.name,
                    "project": "transfer-station",
                    "roles": ["transfer-station narrator"],
                    "reuse_scope": "transfer-station",
                    "migrated_from": str(ver),
                    "rights": {"clone_consent": "approved-legacy-ts"},
                },
            )
            if transcript.startswith("[TRANSCRIPT PENDING"):
                entry["status"] = "approved-needs-transcript"
                entry["warning"] = "Fill exact transcript before delivery clone"
            anchors.append(entry)
            print("MIGRATE TS", entry["id"], entry["status"])

    # Chengwu draft folder
    if CHENGWU_DRAFT.exists():
        dest = DRAFTS / "VA-CHENGWU-ANIME-INNER-V0"
        dest.mkdir(parents=True, exist_ok=True)
        src_json = CHENGWU_DRAFT / "DRAFT-anchor-VA-CHENGWU-ANIME-INNER-V0.json"
        if src_json.exists():
            shutil.copy2(src_json, dest / "DRAFT.json")
        incoming = dest / "incoming-reference"
        incoming.mkdir(exist_ok=True)
        (incoming / "README.txt").write_text(
            "把程雾参考 WAV + 同名 txt 逐字稿放这里，然后登记批准。\n", encoding="utf-8"
        )
        print("DRAFT chengwu ->", dest)

    # dedupe by id keeping first
    seen = set()
    uniq = []
    for a in anchors:
        if a["id"] in seen:
            continue
        seen.add(a["id"])
        uniq.append(a)

    reg = {
        "schema_version": "voice-v3-1",
        "registry_id": "voice-v3-anchors",
        "engine_default": "Qwen3-TTS-12Hz-1.7B-Base",
        "migrated_at": datetime.now(timezone.utc).isoformat(),
        "anchors": uniq,
        "notes": [
            "Single registry for delivery.",
            "Legacy folders kept read-only.",
            "Chengwu lives under library/drafts until reference approved.",
        ],
    }
    REG.parent.mkdir(parents=True, exist_ok=True)
    REG.write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "anchors": len(uniq), "registry": str(REG)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
