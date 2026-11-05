param([string]$RunId = '20260723-180000')

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ffmpeg = 'E:\AI\Kdenlive\bin\ffmpeg.exe'
$episodeRoot = 'E:\program\1project\video\projects\悬疑动漫\episodes\ua001-door-0213'
$outRoot = Join-Path $episodeRoot "audio\reference-inspired-bgm-preview-v1\$RunId"
$started = Get-Date
function Sha([string]$Path) { (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() }

try {
  New-Item -ItemType Directory -Force -Path $outRoot | Out-Null
  $wav = Join-Path $outRoot 'UA001-reference-inspired-suspense-preview-v1-20s-48k.wav'
  $mp3 = Join-Path $outRoot 'UA001-reference-inspired-suspense-preview-v1-20s.mp3'
  # Original procedural composition: slow low drone, filtered air, and four sparse non-melodic pulses.
  & $ffmpeg -hide_banner -loglevel error -y `
    -f lavfi -i 'anoisesrc=color=pink:amplitude=0.09:r=48000:d=20' `
    -f lavfi -i 'aevalsrc=0.020*sin(2*PI*47*t)*(0.65+0.35*sin(2*PI*0.09*t)):s=48000:d=20' `
    -f lavfi -i 'aevalsrc=0.018*sin(2*PI*62*t)*pow(max(0\,sin(2*PI*0.19*t))\,10):s=48000:d=20' `
    -filter_complex '[0:a]highpass=f=55,lowpass=f=1200,volume=0.050[air];[1:a]volume=0.70[drone];[2:a]lowpass=f=160,volume=0.50[pulse];[air][drone][pulse]amix=inputs=3:normalize=0,volume=0.55,afade=t=in:st=0:d=1.5,afade=t=out:st=17.5:d=2.5[a]' `
    -map '[a]' -c:a pcm_s16le $wav
  if ($LASTEXITCODE -ne 0) { throw 'WAV generation failed.' }
  & $ffmpeg -hide_banner -loglevel error -y -i $wav -c:a libmp3lame -b:a 128k $mp3
  if ($LASTEXITCODE -ne 0) { throw 'MP3 generation failed.' }
  $notesPath = Join-Path $outRoot 'UA001-reference-inspired-suspense-preview-v1-notes.md'
  $notes = @'
# Reference-inspired BGM preview v1

## Read-only reference analysis

- Source duration: 87.45 seconds; AAC, stereo, 48kHz.
- Integrated loudness: approximately -36.9 LUFS; loudness range about 10.2 LU; true peak about -13 dBFS.
- RMS level is roughly -39 dBFS and the signal has continuous low-level content rather than long silence gaps.
- The available FFmpeg-only analysis suggests sparse low-frequency/transient movement instead of a dominant, regular drum groove. This is a feature-level observation, not a transcription.

## Original preview design

This 20-second cue uses locally synthesized filtered pink noise, a slowly moving 47Hz drone, and a non-melodic 0.19Hz low pulse. It contains no downloaded sample, no extracted reference audio, and no copied melody. The cue is intended for optional later review only and has not been muxed into any video.

Suggested full-mix starting point: retain the BGM around -34 to -32 LUFS and duck it 4–6dB under Serena narration.
'@
  [System.IO.File]::WriteAllText($notesPath,$notes,[System.Text.UTF8Encoding]::new($false))
  $manifest=[ordered]@{schema_version='1.0';status='pending_user_review';generated_at=(Get-Date).ToString('o');run_id=$RunId;reference_analysis='Feature-level only; no reference audio copied or retained.';duration_seconds=20;outputs=[ordered]@{wav=$wav;wav_sha256=Sha $wav;mp3=$mp3;mp3_sha256=Sha $mp3;notes=$notesPath;notes_sha256=Sha $notesPath};external_audio_downloaded=$false;muxed_into_video=$false;elapsed_seconds=[Math]::Round(((Get-Date)-$started).TotalSeconds,3)}
  $manifestPath=Join-Path $outRoot 'UA001-reference-inspired-suspense-preview-v1-manifest.json'
  [System.IO.File]::WriteAllText($manifestPath,($manifest|ConvertTo-Json -Depth 5),[System.Text.UTF8Encoding]::new($false))
  Write-Output "SUCCESS mp3=$mp3 wav=$wav manifest=$manifestPath elapsed=$($manifest.elapsed_seconds)"
}
catch { Write-Error $_; exit 1 }
