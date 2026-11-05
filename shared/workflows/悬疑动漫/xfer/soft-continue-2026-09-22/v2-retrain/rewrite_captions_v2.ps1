# rewrite_captions_v2.ps1 — enforce male-distinct captions; strip Chengwu / pretty-boy leakage
$ErrorActionPreference = 'Stop'
$ImgFolder = 'E:\program\1project\video\shared\project-tools\lora\charb-hoodie-male-v2\dataset\img\10_charb_hoodie_male'
if (-not (Test-Path $ImgFolder)) { Write-Error "Missing $ImgFolder — run expand first"; exit 2 }

$forbidden = @('1girl','chengwu','bob cut','grey-blue','black choker','teal scoop','pretty boy','bishounen','lean neck','charb_hoodie,')
$poseHints = @{
  '01-seed' = 'upper body, front three-quarter, looking at viewer'
  '01-seed-masc' = 'upper body, front three-quarter, looking at viewer'
  '02-front-face' = 'close-up face, front view, angular male jaw'
  '03-front-half' = 'half body, front view, broad shoulders, flat chest'
  '04-3q-left' = 'three-quarter view from left, angular male jaw'
  '05-3q-right' = 'three-quarter view from right, angular male jaw'
  '06-profile-left' = 'strict side profile, thicker neck, adam''s apple'
  '07-profile-right' = 'strict side profile right, angular male jaw'
  '08-overshoulder' = 'looking back over shoulder, broad shoulders'
  '09-lookup' = 'slight look-up, thicker neck'
  '10-downcast' = 'slight look-down, masculine face'
  '11-hands-pockets' = 'hands in pocket, broad shoulders, flat chest'
  '12-arms-crossed' = 'arms crossed, broad shoulders, male proportions'
  '13-hood-down' = 'hood down, front view, angular male jaw'
  '14-full-standing' = 'full body, standing, broad shoulders, flat chest, male proportions'
  '15-full-walk' = 'full body, walking, male proportions, flat chest'
  '16-full-sit' = 'full body, sitting, broad shoulders, flat chest'
  '17-3q-smile' = 'three-quarter, slight smile, angular male jaw'
  '18-crouch' = 'full body, crouch, male proportions'
  '19-back-half' = 'back view half body, broad shoulders'
  '20-lean-wall' = 'half body lean, broad shoulders, flat chest'
}

function New-Caption([string]$extra) {
  return ("charb_hoodie_male, 1boy, solo, young adult man, male, " +
    "angular male jaw, squared chin, thicker neck, adam's apple, " +
    "short messy jet black hair, NOT bob cut, warm brown eyes, " +
    "fair skin with warm undertone, broad shoulders, flat chest, masculine proportions, " +
    "oversized dark charcoal navy hoodie with drawstrings, hood down, " +
    "soft cel shading, soft lighting, clean soft lineart, " +
    "masterpiece, best quality, simple soft grey background, $extra")
}

$n = 0
Get-ChildItem $ImgFolder -Filter *.png | ForEach-Object {
  $stem = $_.BaseName
  $extra = $poseHints[$stem]
  if (-not $extra) { $extra = 'upper body, looking at viewer, masculine face' }
  $capPath = Join-Path $ImgFolder ($stem + '.txt')
  $text = New-Caption $extra
  Set-Content -Path $capPath -Value ($text + "`n") -Encoding utf8
  $n++
  Write-Host "wrote $capPath"
}

$bad = Select-String -Path (Join-Path $ImgFolder '*.txt') -Pattern ($forbidden -join '|') -ErrorAction SilentlyContinue
if ($bad) {
  Write-Host "WARN still matched forbidden patterns:"
  $bad | ForEach-Object { Write-Host $_.Filename ':' $_.Line }
  exit 5
}
Write-Host "OK rewrote $n captions; no forbidden tokens."
