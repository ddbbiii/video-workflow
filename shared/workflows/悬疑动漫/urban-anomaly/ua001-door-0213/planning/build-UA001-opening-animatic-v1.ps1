[CmdletBinding()]
param(
    [string]$RunId = (Get-Date -Format 'yyyyMMdd-HHmmss')
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$projectRoot = 'E:\program\1project\video'
$runRoot = Join-Path $projectRoot "production\series\UA001-door-0213\review\runs\UA001-opening-animatic-v1\$RunId"
$sourceRoot = 'E:\program\1project\video\shared\runtime\comfy\models\output\series\urban-anomaly-archives\UA001\20260723-101950'
$audio = 'E:\program\1project\video\projects\悬疑动漫\episodes\ua001-door-0213\audio\preview-v1\UA001-opening-narration-preview-v1.mp3'
$ffmpeg = 'E:\AI\Kdenlive\bin\ffmpeg.exe'
$ffprobe = 'E:\AI\Kdenlive\bin\ffprobe.exe'
$font = 'C\:/Windows/Fonts/consola.ttf'

function Require-File([string]$Path, [string]$Name) { if(-not(Test-Path -LiteralPath $Path -PathType Leaf)){throw "$Name missing: $Path"}; return (Resolve-Path -LiteralPath $Path).Path }
function Sha([string]$Path) { return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() }

New-Item -ItemType Directory -Force -Path $runRoot | Out-Null
$archive = Require-File (Join-Path $sourceRoot 'UA001-UI-001-A_00001_.png') 'Archive UI base'
$corridor = Require-File (Join-Path $sourceRoot 'UA001-SCN-001-A_00001_.png') 'Corridor base'
$door = Require-File (Join-Path $sourceRoot 'UA001-SCN-002-A_00001_.png') 'Door base'
$inner = Require-File (Join-Path $sourceRoot 'UA001-SCN-003-A_00001_.png') 'Inner corridor base'
$audio = Require-File $audio 'Serena A narration'
Require-File $ffmpeg 'FFmpeg' | Out-Null
Require-File $ffprobe 'FFprobe' | Out-Null

$visual = Join-Path $runRoot 'UA001-opening-animatic-v1-visual.mp4'
$withNarration = Join-Path $runRoot 'UA001-opening-animatic-v1-narration.mp4'
$srt = Join-Path $runRoot 'UA001-opening-animatic-v1-optional.srt'
$ass = Join-Path $runRoot 'UA001-opening-animatic-v1-optional.ass'
$uiAss = Join-Path $runRoot 'UA001-opening-animatic-v1-ui-overlay.ass'
$filterPath = Join-Path $runRoot 'UA001-opening-animatic-v1-filtergraph.txt'
$started = Get-Date

$uiAssText = @"
[Script Info]
ScriptType: v4.00+
PlayResX: 1280
PlayResY: 720

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: UI,Consolas,25,&H00F5E9D7,&H000000FF,&H660C1118,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,110,60,105,1
Style: UIBottom,Consolas,18,&H00E8DCC8,&H000000FF,&H660C1118,&H00000000,0,0,0,0,100,100,0,0,1,0,0,1,68,60,58,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
Dialogue: 0,0:00:00.00,0:00:05.00,UI,,0,0,0,,URBAN ANOMALY ARCHIVE  /  UA-001\NCASE STATUS: OPEN
Dialogue: 0,0:00:05.00,0:00:15.00,UIBottom,,0,0,0,,B-BLOCK / FLOOR 7
Dialogue: 0,0:00:15.00,0:00:25.00,UI,,0,0,0,,REC CAM-02   02:13:00
Dialogue: 0,0:00:25.00,0:00:35.00,UIBottom,,0,0,0,,OBSERVATION FEED / SIGNAL UNSTABLE
"@
[System.IO.File]::WriteAllText($uiAss, $uiAssText.Trim() + "`n", [System.Text.UTF8Encoding]::new($false))
$uiAssFilter = ([System.IO.Path]::GetFullPath($uiAss)).Replace('\', '/').Replace(':', '\:').Replace("'", "\\'")

# 35 seconds: 5s archive UI, 10s corridor, 10s door, 10s inner corridor.
# No random shake; light, timestamp and scanlines are deterministic FFmpeg overlays.
$filter = @"
[0:v]scale=1360:765,crop=1280:720:x='40+8*sin(t*0.5)':y='22',trim=duration=5,setpts=PTS-STARTPTS,drawbox=x=72:y=68:w=1136:h=584:color=0x7ea8c9@0.36:t=2[v0];
[1:v]scale=1390:782,crop=1280:720:x='55+18*t/10':y='31',trim=duration=10,setpts=PTS-STARTPTS,eq=brightness=-0.04:saturation=0.82[v1];
[2:v]scale=1410:793,crop=1280:720:x='68-14*t/10':y='36',trim=duration=10,setpts=PTS-STARTPTS,eq=brightness=-0.08:saturation=0.80,drawbox=x=870:y=96:w=16:h=530:color=0xc8f5ff@0.16:t=fill,drawbox=x=861:y=96:w=2:h=530:color=0xe2fbff@0.78:t=fill,drawbox=x=46:y=46:w=1188:h=628:color=0x8caabd@0.28:t=2[v2];
[3:v]scale=1400:788,crop=1280:720:x='56+20*t/10':y='34',trim=duration=10,setpts=PTS-STARTPTS,eq=brightness=-0.12:saturation=0.72,drawbox=x=0:y=0:w=1280:h=720:color=0x10263c@0.12:t=fill[v3];
[v0][v1][v2][v3]concat=n=4:v=1:a=0,format=yuv420p,ass=filename='$uiAssFilter'[v]
"@
[System.IO.File]::WriteAllText($filterPath, $filter.Trim() + "`n", [System.Text.UTF8Encoding]::new($false))

& $ffmpeg -hide_banner -y -loop 1 -framerate 24 -i $archive -loop 1 -framerate 24 -i $corridor -loop 1 -framerate 24 -i $door -loop 1 -framerate 24 -i $inner -i $audio -filter_complex_script $filterPath -map '[v]' -t 35 -r 24 -an -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p $visual
if($LASTEXITCODE -ne 0){throw 'Visual animatic export failed.'}
& $ffmpeg -hide_banner -y -i $visual -i $audio -filter_complex '[1:a]apad=pad_dur=8,atrim=duration=35[a]' -map 0:v:0 -map '[a]' -c:v copy -c:a aac -b:a 192k -shortest $withNarration
if($LASTEXITCODE -ne 0){throw 'Narration animatic export failed.'}

$srtText = @"
1
00:00:00,400 --> 00:00:05,300
这份档案的编号是 UA-001。

2
00:00:05,500 --> 00:00:13,200
它记录的不是一间凶宅，也不是一桩失踪案。

3
00:00:13,400 --> 00:00:21,700
最初，所有人都以为问题只是一扇没锁好的门。

4
00:00:21,900 --> 00:00:27,840
每天凌晨两点十三分，旧城区 B 座七层尽头那扇贴着封条的防火门，都会自己打开。
"@
[System.IO.File]::WriteAllText($srt, $srtText.Trim() + "`n", [System.Text.UTF8Encoding]::new($false))
$assText = @"
[Script Info]
ScriptType: v4.00+
PlayResX: 1280
PlayResY: 720

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Default,Microsoft YaHei,34,&H00F4F7F9,&H000000FF,&HAA10151B,&H78000000,0,0,0,0,100,100,0,0,1,2,0,2,60,60,46,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
Dialogue: 0,0:00:00.40,0:00:05.30,Default,,0,0,0,,这份档案的编号是 UA-001。
Dialogue: 0,0:00:05.50,0:00:13.20,Default,,0,0,0,,它记录的不是一间凶宅，也不是一桩失踪案。
Dialogue: 0,0:00:13.40,0:00:21.70,Default,,0,0,0,,最初，所有人都以为问题只是一扇没锁好的门。
Dialogue: 0,0:00:21.90,0:00:27.84,Default,,0,0,0,,每天凌晨两点十三分，旧城区 B 座七层尽头那扇贴着封条的防火门，都会自己打开。
"@
[System.IO.File]::WriteAllText($ass, $assText.Trim() + "`n", [System.Text.UTF8Encoding]::new($false))

$probe = & $ffprobe -v error -show_entries format=duration:stream=codec_name,width,height,avg_frame_rate -of json -- $withNarration | ConvertFrom-Json
$elapsed = [math]::Round(((Get-Date)-$started).TotalSeconds,2)
$manifest = [ordered]@{
    run_id=$RunId; status='pending-user-review'; created_at=$started.ToString('o'); elapsed_seconds=$elapsed
    purpose='UA001 35-second opening animatic: 2D camera motion and deterministic overlays only'
    constraints=@('no LTX','no interpolation','no burned subtitles','no ComfyUI canvas changes','no formal asset import')
    source_audio_requested_path='E:\program\1project\video\production\series\UA001-door-0213\audio\preview-v1\UA001-opening-narration-preview-v1.mp3'
    source_audio_actual_path=$audio; source_audio_duration_seconds=27.84; output_duration_seconds=35
    audio_note='The approved Serena A preview is 27.84 seconds; the final 7.16 seconds are intentional visual-only outro silence, not time-stretched narration.'
    sources=@($archive,$corridor,$door,$inner|ForEach-Object{[ordered]@{path=$_;sha256=(Sha $_)}})
    outputs=[ordered]@{visual_no_subtitle=$visual;narration_no_subtitle=$withNarration;optional_srt=$srt;optional_ass=$ass;ui_overlay_ass=$uiAss;video_sha256=(Sha $withNarration);visual_sha256=(Sha $visual)}
    technical=[ordered]@{resolution='1280x720';fps=24;interpolation='not used';video_model='not used';subtitle_burned=$false;filtergraph=$filterPath}
    approval_gate='Review-only. No output may be promoted, added to a ComfyUI approved input list, or used as a final episode segment without explicit user approval.'
}
$manifestPath=Join-Path $runRoot 'UA001-opening-animatic-v1-manifest.json'
[System.IO.File]::WriteAllText($manifestPath, ($manifest|ConvertTo-Json -Depth 12), [System.Text.UTF8Encoding]::new($false))
[pscustomobject]@{run_root=$runRoot;video=$withNarration;visual=$visual;srt=$srt;ass=$ass;manifest=$manifestPath;elapsed_seconds=$elapsed;sha256=(Sha $withNarration)}|ConvertTo-Json -Compress
