[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$RunId)

$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$projectRoot='E:\program\1project\video'
$runRoot=Join-Path $projectRoot "production\series\urban-anomaly-archives\episodes\UA001-door-0213\final-runs\UA001-full-v1\$RunId"
$segmentRoot=Join-Path $runRoot 'visual-segments'
$sourceRoot='E:\program\1project\video\shared\runtime\comfy\models\output\series\urban-anomaly-archives\UA001\20260723-101950'
function Sha([string]$Path){(Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()}
$plan=@(
@('S01',35,'00:00–00:35'),@('S02',45,'00:35–01:20'),@('S03',50,'01:20–02:10'),@('S04',50,'02:10–03:00'),@('S05',55,'03:00–03:55'),@('S06',60,'03:55–04:55'),@('S07',65,'04:55–06:00'),@('S08',70,'06:00–07:10'),@('S09',75,'07:10–08:20'),@('S10',65,'08:20–09:25'),@('S11',70,'09:25–10:35'),@('S12',50,'10:35–11:25')
)
$segments=@();foreach($item in $plan){$path=Join-Path $segmentRoot "UA001-$($item[0])-visual.mp4";if(-not(Test-Path -LiteralPath $path -PathType Leaf)){throw "Missing visual segment: $path"};$segments += [ordered]@{id=$item[0];duration_seconds=$item[1];section=$item[2];output=$path;sha256=(Sha $path);status='visual-ready-pending-audio'}}
$sources=@();Get-ChildItem $sourceRoot -File -Filter 'UA001-*_00001_.png'|ForEach-Object{$sources += [ordered]@{path=$_.FullName;sha256=(Sha $_.FullName)}}
$manifest=[ordered]@{run_id=$RunId;status='visual-segments-ready-pending-full-audio';finalized_at=(Get-Date).ToString('o');resolution='1280x720';fps=24;provisional_total_seconds=685;constraints=@('2D only','no new image generation','no ComfyUI execution','no LTX','no interpolation','no burned subtitles','not a final episode export');source_assets=$sources;segments=$segments;subtitle_status='pending actual full-v1 narration timing; optional SRT/ASS must be generated after audio';audio_status='waiting for UA001 full-v1 narration';approval_gate='Review-only visual segments. No automatic formal-asset promotion or final delivery.'}
$target=Join-Path $runRoot 'UA001-full-v1-visual-segments-manifest.json';[System.IO.File]::WriteAllText($target,($manifest|ConvertTo-Json -Depth 12),[System.Text.UTF8Encoding]::new($false));[pscustomobject]@{manifest=$target;segments=$segments.Count;provisional_total_seconds=685}|ConvertTo-Json -Compress
