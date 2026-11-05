# geomag full r1: full-length encodes (NVENC under shared gpu.lock) + CPU QA. Progress -> PROGRESS.md
$ErrorActionPreference = 'Continue'
$O = 'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal'; Set-Location $O  # 2026-10-08 迁移：工作目录改为单集根，下面的相对路径都相对单集根
$Lock = 'E:\program\1project\video\shared\work\cache\gpu.lock'
$OldLock = 'E:\program\1project\video\shared\work\cache\gpu.lock'
$RID = 'zhumian-geomag-full-r1-nvenc-20261008'
$Req = "E:\program\1project\video\shared\gpu-queue\requests\$RID.json"
$State = 'E:\program\1project\video\shared\gpu-queue\STATE.md'
$PG = Join-Path $O 'logs\full_r1\PROGRESS.md'
$env:TEMP = 'E:\program\1project\video\shared\work\scratch\zhumian-geomag-full_r1-tmp'; $env:TMP = $env:TEMP; New-Item -ItemType Directory -Force $env:TEMP | Out-Null
$enc = New-Object Text.UTF8Encoding $false
function Now { (Get-Date).ToString('yyyy-MM-ddTHH:mm:ss+08:00') }
function PG($m){ [IO.File]::AppendAllText($PG, ('- [{0}] {1}' -f (Get-Date -Format 'HH:mm:ss'), $m) + "`r`n", $enc) }
function SetReq($st, $extra){ $j = Get-Content $Req -Raw -Encoding UTF8 | ConvertFrom-Json; $j.status = $st; foreach($k in $extra.Keys){ $j | Add-Member -NotePropertyName $k -NotePropertyValue $extra[$k] -Force }; [IO.File]::WriteAllText($Req, ($j | ConvertTo-Json -Depth 5), $enc) }
function Busy($p){ return (Test-Path $p) }
$BODY = 'video\source\geomag_v3_body_r1.mp4'
$NV = '-c:v h264_nvenc -preset p6 -tune hq -rc vbr -cq 18 -b:v 16M -maxrate 24M -bufsize 48M -profile:v high -pix_fmt yuv420p -g 60 -bf 3 -spatial-aq 1 -temporal-aq 1'
$SEG = '[s1]trim=end_frame=667,setsar=1,format=yuv420p,setpts=N/30/TB[b];[2:v]setsar=1,format=yuv420p,setpts=N/30/TB[c];[s2]trim=start_frame=854,setsar=1,format=yuv420p,setpts=N/30/TB[d];'
function FF($name, $argstr, $total){
  $prog = "logs\full_r1\enc_$name.progress"; $log = "logs\full_r1\enc_$name.log"
  PG "START $name (frames=$total)"; $t = Get-Date
  $p = Start-Process -FilePath ffmpeg -ArgumentList ("-hide_banner -nostdin -n -progress $prog " + $argstr) -NoNewWindow -PassThru -RedirectStandardError $log
  $h = $p.Handle
  while(-not $p.HasExited){ Start-Sleep 60; if(Test-Path $prog){ $f = (Select-String -Path $prog -Pattern '^frame=(\d+)' | select -Last 1).Matches.Groups[1].Value; $sp = (Select-String -Path $prog -Pattern '^speed=(.*)' | select -Last 1).Matches.Groups[1].Value; PG "  $name frame $f/$total speed $sp" } }
  $p.WaitForExit(); $ec = $p.ExitCode
  PG ("END {0} exit={1} elapsed={2:n0}s" -f $name, $ec, ((Get-Date)-$t).TotalSeconds); return $ec }
if(-not (Test-Path $PG)){ [IO.File]::WriteAllText($PG, "# PROGRESS geomag_v3_full_r1`r`n`r`n", $enc) }
New-Item -ItemType Directory -Force video\qa | Out-Null
$req = [ordered]@{ id=$RID; owner_thread='助眠解说（Grok Bot 执行子代理）'; line='助眠解说'; submitted_at=(Now); priority=$null; status='queued';
  task='地磁全片 r1 成片编码：干净母版/正片干净版/片头 用 h264_nvenc（仅 NVENC 编码单元，约 15 分钟，显存 <1GB）'; command_or_workflow_path='E:\program\1project\video\shared\workflows\助眠解说\b-geomagnetic-reversal\edit\geomag_v3_full_r1\scripts\encode_full_r1.ps1';
  working_directory=$O; output_directory=(Join-Path $O 'video'); estimated_minutes=20; estimated_vram_mb=1000; dependencies=@();
  authorization='老大 2026-10-07 授权助眠解说线路自行代管 GPU 请求；2026-10-08 老大批准出地磁完整版'; log_path=$PG }
[IO.File]::WriteAllText($Req, ($req | ConvertTo-Json -Depth 5), $enc)
[IO.File]::AppendAllText($State, "`r`n- $(Get-Date -Format 'yyyy-MM-dd HH:mm')（+08:00）：$RID queued（助眠解说自管，地磁全片 NVENC 编码；锁空闲即放行）。`r`n", $enc)
PG "gpu request $RID queued"
$t0 = Get-Date
while ((Busy $Lock) -or (Busy $OldLock)) { if(((Get-Date)-$t0).TotalMinutes -gt 90){ PG 'ABORT: gpu.lock busy > 90 min'; SetReq 'queued' @{ note='lock busy 90 min' }; exit 9 }; PG 'gpu.lock present, waiting 60s'; Start-Sleep 60 }
try { $fs = [IO.File]::Open($Lock, 'CreateNew', 'Write'); $txt = (@{ owner='助眠解说'; holder='助眠解说'; purpose='geomag full r1 NVENC encode'; pid=$PID; started=(Get-Date -Format 'yyyy-MM-dd HH:mm:ss'); request=$RID } | ConvertTo-Json -Compress); $b = $enc.GetBytes($txt); $fs.Write($b,0,$b.Length); $fs.Close(); PG "gpu.lock acquired pid=$PID" } catch { PG "lock fail: $($_.Exception.Message)"; SetReq 'queued' @{ note='lock create failed' }; exit 5 }
SetReq 'running' @{ granted_by='助眠解说自管（老大授权）'; granted_at=(Now); started_at=(Now); pid=$PID }
$ecs = @{}
try {
  $fc1 = '[1:v]split=2[s1][s2];[0:v]setsar=1,format=yuv420p,setpts=N/30/TB[a];' + $SEG + '[a][b][c][d]concat=n=4:v=1:a=0[v]'
  $ecs.full_clean = FF 'full_clean' "-i video\intro\full_r1_src\intro_video_r1.mkv -i $BODY -i video\clips\full_r1_c06b\region_c06b_r1.mkv -i audio\geomag_full_r1_full_mix.wav -filter_complex $fc1 -map [v] -map 3:a -af apad -t 1408.4 -r 30 $NV -c:a aac -b:a 256k -ar 48000 -movflags +faststart video\geomag_v3_full_r1_clean.mp4" 42252
  $fc2 = '[0:v]split=2[s1][s2];[1:v]null[c0];' + $SEG.Replace('[2:v]','[c0]') + '[b][c][d]concat=n=3:v=1:a=0[v]'
  $ecs.body_clean = FF 'body_clean' "-i $BODY -i video\clips\full_r1_c06b\region_c06b_r1.mkv -i audio\geomag_full_r1_body_mix.wav -filter_complex $fc2 -map [v] -map 2:a -af apad -t 1394.4333 -r 30 $NV -c:a aac -b:a 256k -ar 48000 -movflags +faststart video\geomag_v3_full_r1_bodyonly_clean.mp4" 41833
  $ecs.intro_clean = FF 'intro_clean' "-i video\intro\full_r1_src\intro_video_r1.mkv -i audio\geomag_full_r1_stem_intro_narration.wav -map 0:v -map 1:a -t 13.9667 -r 30 $NV -c:a aac -b:a 256k -ar 48000 -movflags +faststart video\intro\geomag_full_r1_intro_clean.mp4" 419
  # burned: from clean master, audio stream copy (subtitles.md)
  if($ecs.full_clean -eq 0){ $ecs.full_sub = FF 'full_subtitled' "-i video\geomag_v3_full_r1_clean.mp4 -map 0:v -map 0:a -vf subtitles=filename=audio/subtitles/full_r1/geomag_full_r1.ass:fontsdir=../../../../assets/助眠解说/subtitles/style-r4/fonts $NV -c:a copy -movflags +faststart video\geomag_v3_full_r1_subtitled.mp4" 42252 }
  if($ecs.intro_clean -eq 0){ $ecs.intro_sub = FF 'intro_subtitled' "-i video\intro\geomag_full_r1_intro_clean.mp4 -map 0:v -map 0:a -vf subtitles=filename=audio/subtitles/full_r1/geomag_full_r1_intro.ass:fontsdir=../../../../assets/助眠解说/subtitles/style-r4/fonts $NV -c:a copy -movflags +faststart video\intro\geomag_full_r1_intro_subtitled.mp4" 419 }
} finally {
  try { $l = Get-Content $Lock -Raw | ConvertFrom-Json; if($l.pid -eq $PID){ Remove-Item -LiteralPath $Lock -Force; PG 'gpu.lock released' } else { PG 'lock not ours at release' } } catch { PG "release err: $($_.Exception.Message)" }
  $bad = @($ecs.Values | ? { $_ -ne 0 }).Count
  SetReq ($(if($bad -eq 0){'completed'}else{'failed'})) @{ finished_at=(Now); exit_codes=($ecs | ConvertTo-Json -Compress) }
  [IO.File]::AppendAllText($State, "- $(Get-Date -Format 'yyyy-MM-dd HH:mm')（+08:00）：$RID $(if($bad -eq 0){'completed'}else{'failed'})（助眠解说自管，占 shared\work\cache\gpu.lock，结束即释放）。`r`n", $enc)
}
PG 'QA (CPU) start'
$qa = 'video\qa\qa_probe.txt'
foreach($f in 'video\geomag_v3_full_r1_clean.mp4','video\geomag_v3_full_r1_subtitled.mp4','video\geomag_v3_full_r1_bodyonly_clean.mp4','video\intro\geomag_full_r1_intro_clean.mp4','video\intro\geomag_full_r1_intro_subtitled.mp4'){
  if(Test-Path $f){ Add-Content $qa "== $f" -Encoding UTF8; ffprobe -v error -count_packets -show_entries format=duration,bit_rate:stream=codec_name,width,height,r_frame_rate,nb_read_packets,sample_rate,channels -of compact $f 2>&1 | Add-Content $qa -Encoding UTF8 } }
foreach($f in 'video\geomag_v3_full_r1_clean.mp4','video\geomag_v3_full_r1_subtitled.mp4','video\geomag_v3_full_r1_bodyonly_clean.mp4'){
  if(Test-Path $f){ Add-Content $qa "== ebur128 $f" -Encoding UTF8; ffmpeg -hide_banner -nostdin -i $f -map 0:a -af ebur128=peak=true -f null - 2>&1 | Select-String -Pattern '^\s+(I:|LRA:|Peak:|Threshold:)' | % { $_.Line } | Add-Content $qa -Encoding UTF8 } }
$S = 'video\geomag_v3_full_r1_subtitled.mp4'
if(Test-Path $S){
  ffmpeg -hide_banner -nostdin -n -i $S -vf "fps=1/30,scale=320:-1,tile=8x6" -frames:v 1 video\qa\contact_full_every30s.jpg 2>> logs\full_r1\qa.log
  ffmpeg -hide_banner -nostdin -n -t 14 -i $S -vf "fps=2,scale=384:-1,tile=7x4" -frames:v 1 video\qa\contact_intro_2fps.jpg 2>> logs\full_r1\qa.log
  ffmpeg -hide_banner -nostdin -n -ss 12 -t 6 -i $S -vf "fps=5,scale=320:-1,tile=6x5" -frames:v 1 video\qa\contact_junction_12-18s_5fps.jpg 2>> logs\full_r1\qa.log
  ffmpeg -hide_banner -nostdin -n -ss 34 -t 8 -i $S -vf "fps=4,scale=320:-1,tile=8x4" -frames:v 1 video\qa\contact_c06b_34-42s_4fps.jpg 2>> logs\full_r1\qa.log
  Add-Content $qa '== black/freeze first 60s (clean)' -Encoding UTF8
  ffmpeg -hide_banner -nostdin -t 60 -i video\geomag_v3_full_r1_clean.mp4 -vf "blackdetect=d=0.2:pix_th=0.08,freezedetect=n=0.001:d=1.5" -an -f null - 2>&1 | Select-String -Pattern 'black_start|freeze_start|freeze_duration' | % { $_.Line } | Add-Content $qa -Encoding UTF8
}
PG "ALL DONE exit_codes=$($ecs | ConvertTo-Json -Compress)"