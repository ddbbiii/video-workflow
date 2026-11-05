# Mix a voice stem onto a picture mp4. Keeps video stream; ducks bed under VO.
param(
  [Parameter(Mandatory = $true)][string]$Video,
  [Parameter(Mandatory = $true)][string]$Voice,
  [Parameter(Mandatory = $true)][string]$Out,
  [double]$VoiceVol = 1.0,
  [double]$BedVol = 0.18
)
$ErrorActionPreference = "Stop"
if (-not (Test-Path $Video)) { throw "missing video $Video" }
if (-not (Test-Path $Voice)) { throw "missing voice $Voice" }
$fc = "[0:a]volume=$BedVol[a0];[1:a]volume=$VoiceVol,apad[a1];[a0][a1]amix=inputs=2:duration=first:dropout_transition=2[aout]"
ffmpeg -hide_banner -y -i $Video -i $Voice -filter_complex $fc -map 0:v -map "[aout]" -c:v copy -c:a aac -b:a 192k -shortest $Out
Write-Host "WROTE $Out"
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 $Out
