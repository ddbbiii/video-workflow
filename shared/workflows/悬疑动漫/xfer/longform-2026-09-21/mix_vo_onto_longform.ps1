# Mix condensed (or full) VO onto longform xfade. Run after picture ready.
param(
  [string]$Video = "E:\program\1project\video\shared\work\scratch\legacy-numbered\longform-2026-09-21\chengwu-home-longform-xfade.mp4",
  [string]$Voice = "E:\program\1project\video\xfer\longform-2026-09-21\tts\CONDENSED-monologue.mp3",
  [string]$Out = "E:\program\1project\video\xfer\longform-2026-09-21\chengwu-horror-vo-mix.mp4",
  [double]$VoiceVol = 1.0,
  [double]$BedVol = 0.18
)
$ErrorActionPreference = "Stop"
if (-not (Test-Path $Video)) { throw "missing video $Video" }
if (-not (Test-Path $Voice)) { throw "missing voice $Voice" }
# duck bed under voice: amix
$fc = "[0:a]volume=$BedVol[a0];[1:a]volume=$VoiceVol[a1];[a0][a1]amix=inputs=2:duration=first:dropout_transition=2[aout]"
ffmpeg -y -i $Video -i $Voice -filter_complex $fc -map 0:v -map "[aout]" -c:v copy -c:a aac -b:a 192k -shortest $Out
Write-Host "WROTE $Out"
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 $Out
