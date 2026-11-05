# -*- coding: utf-8 -*-
"""mariana-descent(下潜一万米)音频参数。

2026-10-19 用户授权"自己看情况往下推进,直到做出最终视频",声线沿用本线路
newton-to-chaos → siffre-beyond-time 连续两期的 b2-warm-male 轻语气配置
(2026-10-13 用户批准声线,2026-10-19 siffre 期沿用确认)。
atempo/BGM 增益同先例;留白口径与 SHOT_PLAN 一致。
参数出处:episodes/siffre-beyond-time/runs/20261018-sbt-b01/scripts/AUDIO_PLAN.py
        ← episodes/newton-to-chaos/audio/AUDIO_PLAN.md。
"""
from __future__ import annotations

# ---- 声线 ----
VOICE_PROFILE_JSON = r"E:\program\1project\video\shared\runtime\engines\tts\voice-assets\b2-warm-male\light-expression-profile.json"
VOICE_TAG = "lightexpr-seed7"       # vo-raw / vo-processed 子目录名,同 newton/siffre

# ---- TTS 引擎 ----
TTS_VENV_PY = r"E:\program\1project\video\shared\runtime\engines\tts\voxcpm\.venv\Scripts\python.exe"
TTS_GEN_SCRIPT = r"E:\program\1project\video\shared\runtime\engines\tts\voxcpm\gen_shots.py"
TTS_MODEL_DIR = r"E:\program\1project\video\shared\runtime\engines\tts\voxcpm\pretrained_models\VoxCPM2"

# ---- VO 后处理 ----
ATEMPO = 0.774224                    # = 0.7304 × 1.06,newton 批准链等价单步,不重复变速

# ---- 混音 ----
BGM_GAIN_DB = -10.0                  # BGM 低于旁白 RMS(newton/siffre 最终值)

# ---- 留白(与 SHOT_PLAN 口径一致) ----
HEAD_S = 0.3774                # 整章头部留白
UNIT_GAP_S = 0.19              # 同段内单元间
PARA_GAP_S = 0.4245            # 段间
CHAP_GAP_S = 0.7547            # 章间
SR = 48000

# ---- VO 裁切 ----
TRIM_RMS_DB = -45.0
TRIM_FRAME_MS = 20
TRIM_KEEP_HEAD = 0.10
TRIM_KEEP_TAIL = 0.15


def require_audio_plan(*names: str) -> dict:
    """运行前检查:列出的参数必须已回填,否则报错退出并列出缺失项。"""
    table = {
        "VOICE_PROFILE_JSON": VOICE_PROFILE_JSON,
        "VOICE_TAG": VOICE_TAG,
        "TTS_VENV_PY": TTS_VENV_PY,
        "TTS_GEN_SCRIPT": TTS_GEN_SCRIPT,
        "TTS_MODEL_DIR": TTS_MODEL_DIR,
        "ATEMPO": ATEMPO,
        "BGM_GAIN_DB": BGM_GAIN_DB,
    }
    missing = [n for n in names if table.get(n) is None]
    if missing:
        raise SystemExit(
            "[待 AUDIO_PLAN] 以下参数尚未定稿,禁止按猜测运行: "
            + ", ".join(missing)
            + "\n请在 runs/20261019-mdb-b01/scripts/AUDIO_PLAN.py 回填后重试。")
    return {n: table[n] for n in names}
