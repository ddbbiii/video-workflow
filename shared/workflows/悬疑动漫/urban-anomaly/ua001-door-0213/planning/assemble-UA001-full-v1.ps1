param(
  [string]$RunId = '20260723-110000'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$projectRoot = 'E:\program\1project\video\projects\悬疑动漫\episodes\ua001-door-0213'
$runRoot = Join-Path $projectRoot "final-runs\UA001-full-v1\$RunId"
$audioRoot = Join-Path $projectRoot 'audio\full-v1-corrected'
$ffmpeg = 'E:\AI\Kdenlive\bin\ffmpeg.exe'
$ffprobe = 'E:\AI\Kdenlive\bin\ffprobe.exe'
$visualManifestPath = Join-Path $runRoot 'UA001-full-v1-visual-segments-manifest.json'
$audioManifestPath = Join-Path $audioRoot 'UA001-full-narration-v1-final-manifest.json'
$started = Get-Date

function Get-Sha256([string]$Path) {
  return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Get-Probe([string]$Path) {
  $raw = & $ffprobe -v error -show_entries 'format=duration:stream=index,codec_type,codec_name,width,height,avg_frame_rate' -of json $Path
  if ($LASTEXITCODE -ne 0) { throw "ffprobe failed: $Path" }
  return ($raw | ConvertFrom-Json)
}

function Get-Stream([object]$Probe, [string]$Type) {
  return @($Probe.streams | Where-Object { $_.codec_type -eq $Type }) | Select-Object -First 1
}

function Assert-ExpectedHash([string]$Path, [string]$Expected, [string]$Label) {
  if (-not (Test-Path -LiteralPath $Path)) { throw "$Label missing: $Path" }
  $actual = Get-Sha256 $Path
  if ($Expected -and ($actual -ne $Expected.ToLowerInvariant())) { throw "$Label SHA-256 mismatch: $actual != $Expected" }
  return $actual
}

function Get-SrtSeconds([string]$Value) {
  if ($Value -notmatch '^(\d{2}):(\d{2}):(\d{2}),(\d{3})$') { throw "Invalid SRT timestamp: $Value" }
  return ([int]$Matches[1] * 3600) + ([int]$Matches[2] * 60) + [int]$Matches[3] + ([int]$Matches[4] / 1000.0)
}

function Test-SrtTimeline([string]$Path, [double]$Total) {
  $matches = [regex]::Matches((Get-Content -LiteralPath $Path -Raw), '(?m)^(\d{2}:\d{2}:\d{2},\d{3})\s+-->\s+(\d{2}:\d{2}:\d{2},\d{3})\r?$')
  if ($matches.Count -lt 1) { throw 'SRT has no cue timestamps.' }
  $previousEnd = 0.0
  foreach ($m in $matches) {
    $start = Get-SrtSeconds $m.Groups[1].Value
    $end = Get-SrtSeconds $m.Groups[2].Value
    if ($start -lt 0 -or $end -lt $start -or $end -gt ($Total + 0.15) -or $start -lt ($previousEnd - 0.15)) {
      throw "SRT timing invalid at $($m.Value)"
    }
    $previousEnd = $end
  }
  return [ordered]@{ cue_count = $matches.Count; first_start_seconds = Get-SrtSeconds $matches[0].Groups[1].Value; last_end_seconds = Get-SrtSeconds $matches[$matches.Count - 1].Groups[2].Value }
}

try {
  foreach ($required in @($ffmpeg, $ffprobe, $visualManifestPath, $audioManifestPath)) {
    if (-not (Test-Path -LiteralPath $required)) { throw "Required file missing: $required" }
  }
  $visualManifest = Get-Content -LiteralPath $visualManifestPath -Raw | ConvertFrom-Json
  $audioManifest = Get-Content -LiteralPath $audioManifestPath -Raw | ConvertFrom-Json
  if ($audioManifest.status -ne 'complete') { throw "Audio manifest status is not complete: $($audioManifest.status)" }

  $totalWav = [string]$audioManifest.total_wav
  $sourceSrt = Join-Path $audioRoot 'UA001-full-narration-v1.srt'
  $sourceAss = Join-Path $audioRoot 'UA001-full-narration-v1.ass'
  $audioHashes = $audioManifest.sha256
  $wavSha = Assert-ExpectedHash $totalWav ([string]$audioHashes.wav) 'Master WAV'
  $srtSha = Assert-ExpectedHash $sourceSrt ([string]$audioHashes.srt) 'Source SRT'
  $assSha = Assert-ExpectedHash $sourceAss ([string]$audioHashes.ass) 'Source ASS'
  $audioDuration = [double]$audioManifest.total_duration_seconds
  $audioSegments = @($audioManifest.segments)
  $visualSegments = @($visualManifest.segments)
  if ($audioSegments.Count -ne 12 -or $visualSegments.Count -ne 12 -or $audioSegments.Count -ne $visualSegments.Count) {
    throw "Expected 12 matching audio/visual segments; got audio=$($audioSegments.Count), visual=$($visualSegments.Count)"
  }

  $remapDir = Join-Path $runRoot 'visual-remapped-by-audio'
  New-Item -ItemType Directory -Force -Path $remapDir | Out-Null
  $remapped = @()
  for ($i = 0; $i -lt $audioSegments.Count; $i++) {
    $a = $audioSegments[$i]
    $v = $visualSegments[$i]
    $expectedSegmentId = ('S{0:D2}' -f ($i + 1))
    $visualSegmentId = if ($v.PSObject.Properties.Name -contains 'id') { [string]$v.id } else { [string]$v.segment_id }
    if ($visualSegmentId -ne $expectedSegmentId) { throw "Visual segment order mismatch at index $i" }
    $sourceVideo = [string]$v.output
    if (-not (Test-Path -LiteralPath $sourceVideo)) { throw "Visual segment missing: $sourceVideo" }
    $probe = Get-Probe $sourceVideo
    $vs = Get-Stream $probe 'video'
    if (-not $vs -or [int]$vs.width -ne 1280 -or [int]$vs.height -ne 720 -or [string]$vs.avg_frame_rate -ne '24/1') {
      throw "Visual segment spec invalid: $sourceVideo"
    }
    $duration = [double]$a.duration_seconds
    $out = Join-Path $remapDir ('UA001-{0}-visual-remapped.mp4' -f $expectedSegmentId)
    $reuse = $false
    if (Test-Path -LiteralPath $out) {
      $existingProbe = Get-Probe $out
      $existingV = Get-Stream $existingProbe 'video'
      if ($existingV -and [int]$existingV.width -eq 1280 -and [int]$existingV.height -eq 720 -and [string]$existingV.avg_frame_rate -eq '24/1' -and [Math]::Abs(([double]$existingProbe.format.duration) - $duration) -le 0.12) { $reuse = $true }
    }
    if (-not $reuse) {
      & $ffmpeg -hide_banner -loglevel error -y -stream_loop -1 -i $sourceVideo -t ('{0:F6}' -f $duration) -an -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p -r 24 -movflags +faststart $out
      if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $out)) { throw "Visual remap failed: $expectedSegmentId" }
    }
    $outProbe = Get-Probe $out
    $outVs = Get-Stream $outProbe 'video'
    $outDuration = [double]$outProbe.format.duration
    if (-not $outVs -or [int]$outVs.width -ne 1280 -or [int]$outVs.height -ne 720 -or [string]$outVs.avg_frame_rate -ne '24/1' -or [Math]::Abs($outDuration - $duration) -gt 0.12) {
      throw "Visual remap QA failed: $expectedSegmentId"
    }
    $remapped += [ordered]@{ segment_id = $expectedSegmentId; narration_id = [string]$a.id; audio_duration_seconds = $duration; source_visual = $sourceVideo; source_visual_sha256 = Get-Sha256 $sourceVideo; remapped_visual = $out; remapped_duration_seconds = $outDuration; remapped_visual_sha256 = Get-Sha256 $out }
  }

  $concatList = Join-Path $remapDir 'concat.txt'
  $concatLines = @($remapped | ForEach-Object { "file '$($_.remapped_visual.Replace("'", "'\\''"))'" })
  [System.IO.File]::WriteAllLines($concatList, [string[]]$concatLines, [System.Text.UTF8Encoding]::new($false))
  $concatVideo = Join-Path $runRoot 'UA001-full-v1-visual-remapped-by-audio.mp4'
  & $ffmpeg -hide_banner -loglevel error -y -f concat -safe 0 -i $concatList -c copy -movflags +faststart $concatVideo
  if ($LASTEXITCODE -ne 0) { throw 'Concat failed.' }

  $finalVideo = Join-Path $runRoot 'UA001-full-v1-no-burned-subtitles.mp4'
  & $ffmpeg -hide_banner -loglevel error -y -i $concatVideo -i $totalWav -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart $finalVideo
  if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $finalVideo)) { throw 'Final mux failed.' }

  $optionalSrt = Join-Path $runRoot 'UA001-full-v1-optional.srt'
  $optionalAss = Join-Path $runRoot 'UA001-full-v1-optional.ass'
  Copy-Item -LiteralPath $sourceSrt -Destination $optionalSrt -Force
  Copy-Item -LiteralPath $sourceAss -Destination $optionalAss -Force
  $copiedSrtSha = Assert-ExpectedHash $optionalSrt $srtSha 'Optional SRT'
  $copiedAssSha = Assert-ExpectedHash $optionalAss $assSha 'Optional ASS'

  $finalProbe = Get-Probe $finalVideo
  $finalV = Get-Stream $finalProbe 'video'
  $finalA = Get-Stream $finalProbe 'audio'
  $finalDuration = [double]$finalProbe.format.duration
  $srtQa = Test-SrtTimeline $optionalSrt $audioDuration
  $assDialogueCount = @((Get-Content -LiteralPath $optionalAss | Where-Object { $_ -like 'Dialogue:*' })).Count
  $qa = [ordered]@{
    passed = $true
    final_duration_seconds = $finalDuration
    master_audio_duration_seconds = $audioDuration
    duration_delta_seconds = [Math]::Abs($finalDuration - $audioDuration)
    video = [ordered]@{ codec = [string]$finalV.codec_name; width = [int]$finalV.width; height = [int]$finalV.height; avg_frame_rate = [string]$finalV.avg_frame_rate }
    audio = [ordered]@{ codec = [string]$finalA.codec_name }
    subtitle_timeline = $srtQa
    ass_dialogue_count = $assDialogueCount
  }
  if (-not $finalV -or -not $finalA -or [string]$finalV.codec_name -ne 'h264' -or [int]$finalV.width -ne 1280 -or [int]$finalV.height -ne 720 -or [string]$finalV.avg_frame_rate -ne '24/1' -or [Math]::Abs($finalDuration - $audioDuration) -gt 0.15 -or $assDialogueCount -lt 1) {
    throw 'Final output QA failed.'
  }

  $manifest = [ordered]@{
    schema_version = '1.0'
    status = 'generated_pending_user_review'
    generated_at = (Get-Date).ToString('o')
    run_id = $RunId
    policy = [ordered]@{ narration_timing = 'actual approved audio duration'; subtitles = 'optional external SRT/ASS only; not burned into master'; visual_generation = 'no regeneration during final assembly' }
    inputs = [ordered]@{
      visual_manifest = $visualManifestPath
      visual_manifest_sha256 = Get-Sha256 $visualManifestPath
      audio_manifest = $audioManifestPath
      audio_manifest_sha256 = Get-Sha256 $audioManifestPath
      master_wav = $totalWav
      master_wav_sha256 = $wavSha
    }
    visual_remap_segments = $remapped
    outputs = [ordered]@{
      video_no_burned_subtitles = $finalVideo
      video_sha256 = Get-Sha256 $finalVideo
      optional_srt = $optionalSrt
      optional_srt_sha256 = $copiedSrtSha
      optional_ass = $optionalAss
      optional_ass_sha256 = $copiedAssSha
      remapped_visual_concat = $concatVideo
      remapped_visual_concat_sha256 = Get-Sha256 $concatVideo
    }
    qa = $qa
    elapsed_seconds = [Math]::Round(((Get-Date) - $started).TotalSeconds, 3)
  }
  $manifestPath = Join-Path $runRoot 'UA001-full-v1-final-manifest.json'
  $qaPath = Join-Path $runRoot 'UA001-full-v1-final-qa.json'
  $json = $manifest | ConvertTo-Json -Depth 8
  [System.IO.File]::WriteAllText($manifestPath, $json, [System.Text.UTF8Encoding]::new($false))
  [System.IO.File]::WriteAllText($qaPath, ($qa | ConvertTo-Json -Depth 6), [System.Text.UTF8Encoding]::new($false))
  Write-Output "SUCCESS final=$finalVideo manifest=$manifestPath elapsed=$($manifest.elapsed_seconds)"
}
catch {
  $failure = [ordered]@{ status = 'failed'; generated_at = (Get-Date).ToString('o'); error = $_.Exception.Message; elapsed_seconds = [Math]::Round(((Get-Date) - $started).TotalSeconds, 3) }
  $failurePath = Join-Path $runRoot 'UA001-full-v1-assembly-failure.json'
  [System.IO.File]::WriteAllText($failurePath, ($failure | ConvertTo-Json -Depth 4), [System.Text.UTF8Encoding]::new($false))
  Write-Error $_
  exit 1
}
