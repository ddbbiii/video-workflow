[CmdletBinding()]
param(
    [string]$RunId = (Get-Date -Format 'yyyyMMdd-HHmmss'),
    [int]$ThrottleLimit = 2
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$projectRoot = 'E:\program\1project\video'
$runRoot = Join-Path $projectRoot "production\series\urban-anomaly-archives\episodes\UA001-door-0213\final-runs\UA001-full-v1\$RunId"
$segmentRoot = Join-Path $runRoot 'visual-segments'
$uiRoot = Join-Path $runRoot 'ui-overlays'
$filterRoot = Join-Path $runRoot 'filtergraphs'
$sourceRoot = 'E:\program\1project\video\shared\runtime\comfy\models\output\series\urban-anomaly-archives\UA001\20260723-101950'
$ffmpeg = 'E:\AI\Kdenlive\bin\ffmpeg.exe'

function Require-File([string]$Path, [string]$Name) { if(-not(Test-Path -LiteralPath $Path -PathType Leaf)){throw "$Name missing: $Path"}; return (Resolve-Path -LiteralPath $Path).Path }
function Sha([string]$Path) { (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() }
function Escape-FilterPath([string]$Path) { ([System.IO.Path]::GetFullPath($Path)).Replace('\','/').Replace(':','\:').Replace("'","\\'") }

Require-File $ffmpeg 'FFmpeg' | Out-Null
New-Item -ItemType Directory -Force -Path $segmentRoot,$uiRoot,$filterRoot | Out-Null
$sources = [ordered]@{
  archive = Require-File (Join-Path $sourceRoot 'UA001-UI-001-A_00001_.png') 'Archive UI base'
  corridor = Require-File (Join-Path $sourceRoot 'UA001-SCN-001-A_00001_.png') 'Corridor base'
  door = Require-File (Join-Path $sourceRoot 'UA001-SCN-002-A_00001_.png') 'Door base'
  inner = Require-File (Join-Path $sourceRoot 'UA001-SCN-003-A_00001_.png') 'Inner corridor base'
  evidence = Require-File (Join-Path $sourceRoot 'UA001-OBJ-003-A_00001_.png') 'Evidence base'
  monitor = Require-File (Join-Path $sourceRoot 'UA001-UI-002-A_00001_.png') 'Monitor UI base'
}

$segments = @(
  [ordered]@{id='S01';duration=35;source='archive';label='UA-001 / CASE OPEN';effect='archive_frame';section='00:00–00:35';note='archive hook'},
  [ordered]@{id='S02';duration=45;source='evidence';label='713 / PROPERTY RECORD';effect='evidence_push';section='00:35–01:20';note='seal and maintenance evidence'},
  [ordered]@{id='S03';duration=50;source='door';label='REC CAM-02 / 02:13:00';effect='door_glow';section='01:20–02:10';note='door gap and cold light'},
  [ordered]@{id='S04';duration=50;source='inner';label='INTERIOR FEED / PERSPECTIVE MISMATCH';effect='inner_fog';section='02:10–03:00';note='interior evidence placeholder'},
  [ordered]@{id='S05';duration=55;source='evidence';label='INCIDENT LOG / EIGHT REPORTS';effect='evidence_push';section='03:00–03:55';note='records and disappearance timeline placeholder'},
  [ordered]@{id='S06';duration=60;source='monitor';label='DUAL CAMERA / CONFLICT DETECTED';effect='monitor_scan';section='03:55–04:55';note='monitor contradiction'},
  [ordered]@{id='S07';duration=65;source='door';label='UNSENT NOTE / PERSONAL ENTRY';effect='door_glow';section='04:55–06:00';note='transfer rule evidence'},
  [ordered]@{id='S08';duration=70;source='inner';label='OBSERVATION RULE / TIME CONFIRMATION';effect='inner_fog';section='06:00–07:10';note='rule reveal'},
  [ordered]@{id='S09';duration=75;source='door';label='VERIFICATION / PAPER UNDER DOOR';effect='door_glow';section='07:10–08:20';note='paper-slide I2V reserved later; current static bridge'},
  [ordered]@{id='S10';duration=65;source='corridor';label='FLOOR 7 / ACCESS SEALED';effect='corridor_lock';section='08:20–09:25';note='sealed-floor escalation'},
  [ordered]@{id='S11';duration=70;source='inner';label='TEMPORARY ADVISORY / DO NOT ANSWER';effect='inner_fog';section='09:25–10:35';note='rules and reverse evidence'},
  [ordered]@{id='S12';duration=50;source='archive';label='CASE STATUS / UNRESOLVED';effect='archive_frame';section='10:35–11:25';note='city expansion/end hook'}
)

$started = Get-Date
$jobs = @()
foreach($segment in $segments){
  $uiAss = Join-Path $uiRoot "UA001-$($segment.id)-ui.ass"
  $uiText = @"
[Script Info]
ScriptType: v4.00+
PlayResX: 1280
PlayResY: 720

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: UI,Consolas,23,&H00E8E0D0,&H000000FF,&H660B1118,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,64,60,62,1
Style: Bottom,Consolas,17,&H00D8CEC2,&H000000FF,&H660B1118,&H00000000,0,0,0,0,100,100,0,0,1,0,0,1,64,60,48,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
Dialogue: 0,0:00:00.00,0:00:$('{0:00}' -f [math]::Min($segment.duration,59)).99,UI,,0,0,0,,$($segment.label)
Dialogue: 0,0:00:00.00,0:00:$('{0:00}' -f [math]::Min($segment.duration,59)).99,Bottom,,0,0,0,,URBAN ANOMALY ARCHIVE  /  UA-001  /  $($segment.id)
"@
  # ASS timing is intentionally limited to first 59 seconds; long segments keep the visual label as a brief establishing overlay only.
  [System.IO.File]::WriteAllText($uiAss, $uiText.Trim()+"`n", [System.Text.UTF8Encoding]::new($false))
  $uiFilter = Escape-FilterPath $uiAss
  $duration = [int]$segment.duration
  $motion = switch($segment.effect){
    'door_glow' { "scale=1410:793,crop=1280:720:x='68-16*t/$duration':y='36',eq=brightness=-0.08:saturation=0.80,drawbox=x=870:y=92:w=16:h=536:color=0xc8f5ff@0.15:t=fill,drawbox=x=861:y=92:w=2:h=536:color=0xe9fcff@0.75:t=fill,drawbox=x=46:y=46:w=1188:h=628:color=0x8caabd@0.24:t=2" }
    'inner_fog' { "scale=1400:788,crop=1280:720:x='56+20*t/$duration':y='34',eq=brightness=-0.12:saturation=0.72,drawbox=x=0:y=0:w=1280:h=720:color=0x10263c@0.10:t=fill" }
    'monitor_scan' { "scale=1360:765,crop=1280:720:x='40+8*sin(t*0.25)':y='22',eq=brightness=-0.05:saturation=0.64,drawbox=x=46:y=46:w=1188:h=628:color=0x8caabd@0.30:t=2,drawbox=x=0:y='120+40*sin(t*1.7)':w=1280:h=2:color=0xa8d4e0@0.16:t=fill" }
    'evidence_push' { "scale=1390:782,crop=1280:720:x='55+18*t/$duration':y='31',eq=brightness=-0.03:saturation=0.74,drawbox=x=46:y=46:w=1188:h=628:color=0x8caabd@0.15:t=2" }
    'corridor_lock' { "scale=1390:782,crop=1280:720:x='55+18*t/$duration':y='31',eq=brightness=-0.07:saturation=0.76,drawbox=x=0:y=0:w=1280:h=720:color=0x0f1d29@0.08:t=fill" }
    default { "scale=1360:765,crop=1280:720:x='40+8*sin(t*0.25)':y='22',eq=brightness=-0.06:saturation=0.72,drawbox=x=72:y=68:w=1136:h=584:color=0x7ea8c9@0.30:t=2" }
  }
  $filterPath = Join-Path $filterRoot "UA001-$($segment.id)-filter.txt"
  $filter = "[0:v]$motion,trim=duration=$duration,setpts=PTS-STARTPTS,format=yuv420p,ass=filename='$uiFilter'[v]"
  [System.IO.File]::WriteAllText($filterPath, $filter+"`n", [System.Text.UTF8Encoding]::new($false))
  $out = Join-Path $segmentRoot "UA001-$($segment.id)-visual.mp4"
  $jobs += [pscustomobject]@{segment=$segment;source=$sources[$segment.source];filter=$filterPath;out=$out;ui_ass=$uiAss}
}

$pending = [System.Collections.Generic.Queue[object]]::new();$jobs|ForEach-Object{$pending.Enqueue($_)};$active=@();$completed=@()
while($pending.Count -gt 0 -or $active.Count -gt 0){
  while($pending.Count -gt 0 -and $active.Count -lt $ThrottleLimit){
    $job=$pending.Dequeue()
    $psJob=Start-Job -ArgumentList $ffmpeg,$job.source,$job.filter,$job.out,$job.segment.duration -ScriptBlock { param($bin,$src,$filter,$out,$duration); & $bin -hide_banner -y -loop 1 -framerate 24 -i $src -filter_complex_script $filter -map '[v]' -t $duration -r 24 -an -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p $out; [pscustomobject]@{exit_code=$LASTEXITCODE;out=$out}|ConvertTo-Json -Compress }
    $active += [pscustomobject]@{job=$job;ps=$psJob}
  }
  Start-Sleep -Milliseconds 300
  foreach($entry in @($active|Where-Object{$_.ps.State -in @('Completed','Failed','Stopped')})){
    $raw=Receive-Job -Job $entry.ps -ErrorAction SilentlyContinue;Remove-Job -Job $entry.ps -Force -ErrorAction SilentlyContinue
    if($entry.ps.State -ne 'Completed'){throw "Segment worker failed: $($entry.job.segment.id)"}
    $result=$raw|Select-Object -Last 1|ConvertFrom-Json
    if($result.exit_code -ne 0 -or -not(Test-Path -LiteralPath $entry.job.out)){throw "Segment export failed: $($entry.job.segment.id)"}
    $completed += [pscustomobject]@{id=$entry.job.segment.id;section=$entry.job.segment.section;duration_seconds=$entry.job.segment.duration;source=$entry.job.source;output=$entry.job.out;ui_ass=$entry.job.ui_ass;filtergraph=$entry.job.filter;sha256=(Sha $entry.job.out);status='visual-ready-pending-audio'}
    $active=@($active|Where-Object{$_.ps.Id -ne $entry.ps.Id})
  }
}

$elapsed=[math]::Round(((Get-Date)-$started).TotalSeconds,2)
$manifest=[ordered]@{run_id=$RunId;status='visual-segments-ready-pending-full-audio';created_at=$started.ToString('o');elapsed_seconds=$elapsed;resolution='1280x720';fps=24;provisional_total_seconds=(($segments|Measure-Object duration -Sum).Sum);constraints=@('2D only','no new image generation','no ComfyUI execution','no LTX','no interpolation','no burned subtitles','not a final episode export');source_assets=($sources.GetEnumerator()|ForEach-Object{[ordered]@{id=$_.Key;path=$_.Value;sha256=(Sha $_.Value)}});segments=$completed;subtitle_status='pending actual full-v1 narration timing; optional SRT/ASS must be generated after audio';audio_status='waiting for UA001 full-v1 narration';approval_gate='Review-only visual segments. No automatic formal-asset promotion or final delivery.'}
$manifestPath=Join-Path $runRoot 'UA001-full-v1-visual-segments-manifest.json';[System.IO.File]::WriteAllText($manifestPath,($manifest|ConvertTo-Json -Depth 12),[System.Text.UTF8Encoding]::new($false))
[pscustomobject]@{run_root=$runRoot;manifest=$manifestPath;segments=$completed.Count;provisional_total_seconds=$manifest.provisional_total_seconds;elapsed_seconds=$elapsed}|ConvertTo-Json -Compress
