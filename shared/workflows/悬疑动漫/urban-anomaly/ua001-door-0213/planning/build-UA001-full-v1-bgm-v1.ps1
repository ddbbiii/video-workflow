param([string]$RunId = '20260723-140000')

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ffmpeg = 'E:\AI\Kdenlive\bin\ffmpeg.exe'
$ffprobe = 'E:\AI\Kdenlive\bin\ffprobe.exe'
$episodeRoot = 'E:\program\1project\video\projects\悬疑动漫\episodes\ua001-door-0213'
$masterRun = Join-Path $episodeRoot 'final-runs\UA001-full-v1\20260723-110000'
$audioRoot = Join-Path $episodeRoot 'audio\full-v1-corrected'
$outRoot = Join-Path $episodeRoot "final-runs\UA001-full-v1-bgm-v1\$RunId"
$duration = 670.821875
$started = Get-Date

function Sha([string]$Path) { (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() }
function Probe([string]$Path) { ((& $ffprobe -v error -show_entries 'format=duration:stream=codec_type,codec_name,width,height,avg_frame_rate' -of json $Path) | ConvertFrom-Json) }

try {
  foreach ($f in @($ffmpeg, $ffprobe, (Join-Path $masterRun 'UA001-full-v1-no-burned-subtitles.mp4'), (Join-Path $audioRoot 'UA001-full-narration-v1-48k-master.wav'))) {
    if (-not (Test-Path -LiteralPath $f)) { throw "Missing required input: $f" }
  }
  New-Item -ItemType Directory -Path $outRoot -Force | Out-Null
  $bed = Join-Path $outRoot 'UA001-bgm-bed-procedural-v1-48k.wav'
  $sfx = Join-Path $outRoot 'UA001-sfx-sparse-procedural-v1-48k.wav'
  $mix = Join-Path $outRoot 'UA001-bgm-sfx-v1-48k.wav'
  $video = Join-Path $outRoot 'UA001-full-v1-bgm-v1-no-burned-subtitles.mp4'
  $cuePath = Join-Path $outRoot 'UA001-bgm-sfx-v1-cues.md'
  $masterVideo = Join-Path $masterRun 'UA001-full-v1-no-burned-subtitles.mp4'
  $narration = Join-Path $audioRoot 'UA001-full-narration-v1-48k-master.wav'

  # Original procedural bed: dark low drone + filtered corridor noise. No third-party audio is used.
  & $ffmpeg -hide_banner -loglevel error -y `
    -f lavfi -i "anoisesrc=color=pink:amplitude=0.12:r=48000:d=$duration" `
    -f lavfi -i "sine=frequency=48:sample_rate=48000:duration=$duration" `
    -f lavfi -i "sine=frequency=73:sample_rate=48000:duration=$duration" `
    -filter_complex '[0:a]highpass=f=45,lowpass=f=1050,volume=0.07[n];[1:a]volume=0.035[d1];[2:a]volume=0.012[d2];[n][d1][d2]amix=inputs=3:normalize=0,volume=0.45,atrim=duration=670.821875[bed]' `
    -map '[bed]' -c:a pcm_s16le $bed
  if ($LASTEXITCODE -ne 0) { throw 'Procedural bed generation failed.' }

  # Sparse narrative cues only: unlock/door (N03), observation knock (N06), paper/record (N09), final lock (N11).
  & $ffmpeg -hide_banner -loglevel error -y `
    -f lavfi -i 'sine=frequency=82:sample_rate=48000:duration=0.28' `
    -f lavfi -i 'sine=frequency=105:sample_rate=48000:duration=0.12' `
    -f lavfi -i 'sine=frequency=98:sample_rate=48000:duration=0.12' `
    -f lavfi -i 'sine=frequency=1480:sample_rate=48000:duration=0.09' `
    -f lavfi -i 'sine=frequency=76:sample_rate=48000:duration=0.25' `
    -filter_complex '[0:a]afade=t=out:st=0:d=0.28,volume=0.08,adelay=100290|100290[c1];[1:a]afade=t=out:st=0:d=0.12,volume=0.055,adelay=323517|323517[c2];[2:a]afade=t=out:st=0:d=0.12,volume=0.045,adelay=323860|323860[c3];[3:a]afade=t=out:st=0:d=0.09,volume=0.022,adelay=447368|447368[c4];[4:a]afade=t=out:st=0:d=0.25,volume=0.065,adelay=623142|623142[c5];[c1][c2][c3][c4][c5]amix=inputs=5:normalize=0,apad,atrim=duration=670.821875[sfx]' `
    -map '[sfx]' -c:a pcm_s16le $sfx
  if ($LASTEXITCODE -ne 0) { throw 'Procedural SFX generation failed.' }

  & $ffmpeg -hide_banner -loglevel error -y -i $bed -i $sfx `
    -filter_complex '[0:a][1:a]amix=inputs=2:normalize=0,volume=0.82,atrim=duration=670.821875[bgm]' `
    -map '[bgm]' -c:a pcm_s16le $mix
  if ($LASTEXITCODE -ne 0) { throw 'BGM/SFX mix generation failed.' }

  # Narration stays as the lead. BGM bus is side-chain ducked by narration at roughly 4–6 dB.
  & $ffmpeg -hide_banner -loglevel error -y -i $masterVideo -i $narration -i $mix `
    -filter_complex '[2:a][1:a]sidechaincompress=threshold=0.028:ratio=4:attack=20:release=500:makeup=1[ducked];[1:a][ducked]amix=inputs=2:normalize=0:weights=1 1[a]' `
    -map 0:v:0 -map '[a]' -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart $video
  if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $video)) { throw 'Final BGM video mux failed.' }

  $cueText = @'
# UA001 BGM + SFX Cue Table v1

All source audio in this run is procedural and generated locally by FFmpeg; no external music/SFX download or third-party sample is used.

| Time | Cue | Intent |
|---|---|---|
| 00:00–11:10 | low drone + filtered pink-noise corridor bed | continuous but low-level dark ambience |
| 01:40.290 | short low door-unlock resonance | first abnormal door reveal |
| 05:23.517 / 05:23.860 | two restrained low knocks | observation-camera contradiction |
| 07:27.368 | faint high paper/record tick | verification record anomaly |
| 10:23.142 | low lock resonance | final rule / end-record tension |

Mix policy: narration is the foreground. The BGM/SFX bus is side-chain ducked by the narration using a 4:1 compressor, calibrated to reduce the background by approximately 4–6 dB while speech is active. No dialogue subtitle is burned into video.
'@
  [System.IO.File]::WriteAllText($cuePath, $cueText, [System.Text.UTF8Encoding]::new($false))

  $p = Probe $video
  $v = @($p.streams | Where-Object codec_type -eq 'video')[0]
  $a = @($p.streams | Where-Object codec_type -eq 'audio')[0]
  $actualDuration = [double]$p.format.duration
  if ($v.codec_name -ne 'h264' -or $a.codec_name -ne 'aac' -or [int]$v.width -ne 1280 -or [int]$v.height -ne 720 -or $v.avg_frame_rate -ne '24/1' -or [Math]::Abs($actualDuration - $duration) -gt 0.15) { throw 'BGM final output QA failed.' }
  $manifest = [ordered]@{
    schema_version = '1.0'; status = 'generated_pending_user_review'; generated_at = (Get-Date).ToString('o'); run_id = $RunId
    source_policy = [ordered]@{ external_audio_downloaded = $false; audio_origin = 'locally procedural FFmpeg synthesis'; original_master_unchanged = $true }
    inputs = [ordered]@{ master_video = $masterVideo; master_video_sha256 = Sha $masterVideo; narration_wav = $narration; narration_wav_sha256 = Sha $narration }
    outputs = [ordered]@{ bgm_bed_wav = $bed; bgm_bed_sha256 = Sha $bed; sparse_sfx_wav = $sfx; sparse_sfx_sha256 = Sha $sfx; bgm_sfx_mix_wav = $mix; bgm_sfx_mix_sha256 = Sha $mix; video_no_burned_subtitles = $video; video_sha256 = Sha $video; cue_table = $cuePath; cue_table_sha256 = Sha $cuePath }
    mix = [ordered]@{ narration = 'Serena A master WAV'; background_ducking = 'sidechaincompress ratio 4:1; target approximately 4–6 dB while narration is active'; subtitles_burned = $false }
    qa = [ordered]@{ passed = $true; duration_seconds = $actualDuration; video_codec = $v.codec_name; audio_codec = $a.codec_name; width = [int]$v.width; height = [int]$v.height; avg_frame_rate = $v.avg_frame_rate }
    explicit_non_operations = @('No ComfyUI changes','No interpolation','No upscaling','No burned subtitles')
    elapsed_seconds = [Math]::Round(((Get-Date)-$started).TotalSeconds,3)
  }
  $manifestPath = Join-Path $outRoot 'UA001-full-v1-bgm-v1-manifest.json'
  [System.IO.File]::WriteAllText($manifestPath, ($manifest | ConvertTo-Json -Depth 6), [System.Text.UTF8Encoding]::new($false))
  Write-Output "SUCCESS video=$video manifest=$manifestPath elapsed=$($manifest.elapsed_seconds)"
}
catch { Write-Error $_; exit 1 }
