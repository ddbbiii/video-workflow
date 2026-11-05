param([string]$RunId = '20260723-160000')

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ffmpeg = 'E:\AI\Kdenlive\bin\ffmpeg.exe'
$episodeRoot = 'E:\program\1project\video\projects\悬疑动漫\episodes\ua001-door-0213'
$outRoot = Join-Path $episodeRoot "audio\bgm-auditions-v1\$RunId"
$duration = '670.821875'
$started = Get-Date
function Sha([string]$Path) { (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() }

try {
  if (-not (Test-Path -LiteralPath $ffmpeg)) { throw 'FFmpeg missing.' }
  New-Item -ItemType Directory -Path $outRoot -Force | Out-Null
  $aWav = Join-Path $outRoot 'UA001-global-bgm-A-minimal-dark-48k.wav'
  $bWav = Join-Path $outRoot 'UA001-global-bgm-B-pulse-industrial-48k.wav'
  $cWav = Join-Path $outRoot 'UA001-global-bgm-C-narrative-ambient-48k.wav'

  # A: Nearly beatless, low-frequency, subdued corridor air.
  & $ffmpeg -hide_banner -loglevel error -y -f lavfi -i "anoisesrc=color=pink:amplitude=0.10:r=48000:d=$duration" -f lavfi -i "sine=frequency=46:sample_rate=48000:duration=$duration" -f lavfi -i "sine=frequency=69:sample_rate=48000:duration=$duration" -filter_complex '[0:a]highpass=f=42,lowpass=f=850,volume=0.045[n];[1:a]volume=0.022[d1];[2:a]volume=0.006[d2];[n][d1][d2]amix=inputs=3:normalize=0,volume=0.55,atrim=duration=670.821875[a]' -map '[a]' -c:a pcm_s16le $aWav
  if ($LASTEXITCODE -ne 0) { throw 'Candidate A failed.' }

  # B: Slow 0.17Hz pulse, muted industrial hum and narrow-band air texture.
  & $ffmpeg -hide_banner -loglevel error -y -f lavfi -i "anoisesrc=color=white:amplitude=0.06:r=48000:d=$duration" -f lavfi -i "aevalsrc=0.034*sin(2*PI*54*t)*pow(max(0\,sin(2*PI*0.17*t))\,8):s=48000:d=$duration" -f lavfi -i "sine=frequency=108:sample_rate=48000:duration=$duration" -filter_complex '[0:a]bandpass=f=410:w=220,volume=0.018[n];[1:a]lowpass=f=180,volume=0.72[p];[2:a]volume=0.004[h];[n][p][h]amix=inputs=3:normalize=0,volume=0.70,atrim=duration=670.821875[a]' -map '[a]' -c:a pcm_s16le $bWav
  if ($LASTEXITCODE -ne 0) { throw 'Candidate B failed.' }

  # C: Still subtle but more narrative motion: two slow drones and a distant rising air bed.
  & $ffmpeg -hide_banner -loglevel error -y -f lavfi -i "anoisesrc=color=pink:amplitude=0.10:r=48000:d=$duration" -f lavfi -i "aevalsrc=0.020*sin(2*PI*43*t)*(0.70+0.30*sin(2*PI*0.006*t)):s=48000:d=$duration" -f lavfi -i "aevalsrc=0.012*sin(2*PI*77*t)*(0.55+0.45*sin(2*PI*0.011*t)):s=48000:d=$duration" -filter_complex '[0:a]highpass=f=70,lowpass=f=1500,volume=0.040[n];[1:a]volume=0.72[d1];[2:a]volume=0.70[d2];[n][d1][d2]amix=inputs=3:normalize=0,volume=0.60,atrim=duration=670.821875[a]' -map '[a]' -c:a pcm_s16le $cWav
  if ($LASTEXITCODE -ne 0) { throw 'Candidate C failed.' }

  $candidates = @(
    [ordered]@{ id='A'; style='极简低频暗氛围'; wav=$aWav; description='几乎无节奏；低频 drone 与过滤走廊空气感。'; ducking_recommendation='如进入正式混音，先设背景总线约 -34 LUFS，再由旁白 duck 约 4 dB。' },
    [ordered]@{ id='B'; style='低频脉冲 + 稀疏工业纹理'; wav=$bWav; description='约 0.17Hz 的慢脉冲，适合档案推进感；不添加叙事音效。'; ducking_recommendation='如进入正式混音，先设背景总线约 -32 LUFS，再由旁白 duck 约 5–6 dB。' },
    [ordered]@{ id='C'; style='叙事推进型悬疑 ambient'; wav=$cWav; description='双低频 drone 的慢速涨落，存在感高于 A/B 但无明确节拍。'; ducking_recommendation='如进入正式混音，先设背景总线约 -33 LUFS，再由旁白 duck 约 5 dB。' }
  )
  foreach ($c in $candidates) {
    $mp3 = [System.IO.Path]::ChangeExtension($c.wav, '.mp3')
    & $ffmpeg -hide_banner -loglevel error -y -i $c.wav -c:a libmp3lame -b:a 128k $mp3
    if ($LASTEXITCODE -ne 0) { throw "MP3 preview failed: $($c.id)" }
    $c.preview_mp3 = $mp3
    $c.wav_sha256 = Sha $c.wav
    $c.preview_mp3_sha256 = Sha $mp3
  }
  $cue = @'
# UA001 Global BGM Auditions v1

These are independent, full-duration audition tracks only. They are not muxed into any UA001 video and contain no door/knock/event SFX.

| Candidate | Character | Recommended use |
|---|---|---|
| A | almost beatless dark low-frequency air | best when narration must stay dominant |
| B | slow pulse plus muted industrial texture | best for a more structured shared/archive/procedural tone |
| C | gently evolving suspense ambient | best for a more cinematic narration arc |

All audio was generated locally with FFmpeg oscillators/noise sources. No external music, samples, or downloads were used.
'@
  $cuePath = Join-Path $outRoot 'UA001-global-bgm-auditions-v1-cue-notes.md'
  [System.IO.File]::WriteAllText($cuePath, $cue, [System.Text.UTF8Encoding]::new($false))
  $manifest = [ordered]@{ schema_version='1.0'; status='pending_user_review'; generated_at=(Get-Date).ToString('o'); run_id=$RunId; duration_seconds=[double]$duration; external_audio_downloaded=$false; muxed_into_video=$false; candidates=$candidates; cue_notes=$cuePath; cue_notes_sha256=Sha $cuePath; elapsed_seconds=[Math]::Round(((Get-Date)-$started).TotalSeconds,3) }
  $manifestPath = Join-Path $outRoot 'UA001-global-bgm-auditions-v1-manifest.json'
  [System.IO.File]::WriteAllText($manifestPath, ($manifest|ConvertTo-Json -Depth 5), [System.Text.UTF8Encoding]::new($false))
  Write-Output "SUCCESS root=$outRoot manifest=$manifestPath elapsed=$($manifest.elapsed_seconds)"
}
catch { Write-Error $_; exit 1 }
