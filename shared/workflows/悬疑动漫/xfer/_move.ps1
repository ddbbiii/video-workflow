$ErrorActionPreference = 'Continue'
$src = 'E:\program\1project\video\xfer'
$dst = 'E:\program\1project\video\projects\悬疑动漫\legacy-xfer'
$rdst = Join-Path $dst '_root-files'
$log = Join-Path $dst '_move.log'
$rlog = Join-Path $dst '_robocopy.log'
function L($m){ $l = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' ' + $m; Add-Content -LiteralPath $log -Value $l -Encoding UTF8 }
function Snap($p){
  $files = @(Get-ChildItem -LiteralPath $p -Recurse -File -Force -ErrorAction SilentlyContinue)
  $sum = [int64]0; foreach($f in $files){ $sum += $f.Length }
  $list = $files | ForEach-Object { $_.FullName.Substring($p.Length) + '|' + $_.Length } | Sort-Object
  [pscustomobject]@{ Count = $files.Count; Bytes = $sum; List = $list }
}
$folders = @('chengwu-assets','chengwu-grok-train','chengwu-lora-smoke','chengwu-raw','chengwu-turnaround-v1','chengwu-voice-prep','voice-candidates-chengwu','longform-2026-09-21','phase-ab-2026-09-23','keyframes-2026-09-23','keyframes-2026-09-28','keyframes-2026-09-29','charb-jacket-prep','charb-jacket-smoke','charb-jacket-smoke-stylelock','charb-jacket-smoke-stylelock-v2','jacket-solo-featA-r5','jacket-solo-featA-style','soft-continue-2026-09-22','retest-2026-09-22','overnight-2026-09-21','overnight-2026-09-22','home-char-smoke','chin-soft-in','pose-refs','refs-for-grok','style-suspense-rainnight-v1','style-suspense-rainnight-v1-smoke','mirror-halfbeat-final','mirror-halfbeat-smoke','sync')
$files = @('_tmp_sweater_B2.py','51b-result.png','51c-result.png','51d-result.png','51e2-result.png','51e3-result.png','51e-result.png','51e-stage1.png','51-identity-v4.png','51-pose-ref.png','51-smoke-result.png','check-hoodie-v2.ps1','check-v2-train.ps1','chengwu-lora-dataset.tgz','chengwu-lora-v1b-dataset.tgz','copy_prev_rest.ps1','home-lora-dataset.tgz','launch_chin_r3.ps1','line-b-51.tar.gz','line-b-52.tar.gz','MONITOR-CHENGWU-TRAIN.ps1','MULTI-CHAR-INTERACTION-PLAN-2026-09-20.md','OPENPOSE-IPADAPTER-INVENTORY-2026-09-20.md','overnight_runner.py','PAUSE-CHECKPOINT-2026-09-24.md','poll_chin_r3.ps1','prep_chin_r3_qc.ps1','pulid-v1-result.png','pulid-v2-result.png','pulid-v3-result.png','pulid-v4-result.png','pulid-v5-result.png','run_51e_twostage.py','run_sdxl_train.py','sd-scripts.tgz','SETUP-AND-TRAIN-CHENGWU-V1.ps1','SETUP-AND-TRAIN-CHENGWU-V2.ps1','smoke_chengwu_hoodie_male_v1_chin_r3.py','smoke_chengwu_hoodie_male_v1_weak.py','smoke_chengwu_hoodie_male_v1_weak_r2.py','smoke_chengwu_jacket_v1_weak.py','smoke_chin_i2i.py','smoke_chin_soft.py','smoke_dual_lora.py','smoke_ep10.py','smoke_h3_from_keyframe.py','smoke_h3_k1_wider.py','smoke_hair_swap.py','smoke_jacket_solo_featA.py','smoke_jacket_solo_featA_r2.py','smoke_jacket_solo_featA_r3.py','smoke_jacket_solo_featA_style.py','smoke_jacket_solo_featA_style_r5.py','smoke_keyframe_openpose.py','smoke_outfit.py','smoke_v1b_vs_v1.py','SMOKE-HOME-CHAR-DUAL-LORA.ps1','suspense-rainnight-v1-corpus.tgz','sync_chin_r3_pass.ps1','train-chengwu-v1b-continue.ps1','train-chengwu-v1-fixed.ps1','train-jiaoli-home-v1.ps1','upperbody-A-ref.png')
L "START folders=$($folders.Count) files=$($files.Count)"
$rows = @()
foreach($d in $folders){
  $s = Join-Path $src $d; $t = Join-Path $dst $d
  if (-not (Test-Path -LiteralPath $s)) { L "MISSING $d"; $rows += [pscustomobject]@{Name=$d;PreC='-';PreB='-';PostC='-';PostB='-';SrcLeft='-';RC='-';Result='SOURCE MISSING'}; continue }
  if (Test-Path -LiteralPath $t) { L "SKIP_DEST_EXISTS $d"; $rows += [pscustomobject]@{Name=$d;PreC='-';PreB='-';PostC='-';PostB='-';SrcLeft='-';RC='-';Result='SKIPPED dest exists'}; continue }
  $pre = Snap $s
  L "PRE $d count=$($pre.Count) bytes=$($pre.Bytes)"
  & robocopy.exe $s $t /E /MOVE /COPY:DAT /DCOPY:T /R:2 /W:2 /NP /NFL /NDL "/LOG+:$rlog" | Out-Null
  $rc = $LASTEXITCODE
  $post = Snap $t
  $left = 0; if (Test-Path -LiteralPath $s) { $left = @(Get-ChildItem -LiteralPath $s -Recurse -Force -ErrorAction SilentlyContinue).Count; if ($left -eq 0) { $left = 'emptydir' } }
  $same = ($pre.Count -eq $post.Count) -and ($pre.Bytes -eq $post.Bytes) -and ((@($pre.List) -join "`n") -eq (@($post.List) -join "`n"))
  $res = if ($same -and $rc -lt 8 -and ($left -eq 0)) { 'OK' } elseif ($same -and $rc -lt 8) { "OK-COPIED src-left=$left" } else { "MISMATCH rc=$rc" }
  L "POST $d count=$($post.Count) bytes=$($post.Bytes) rc=$rc srcleft=$left -> $res"
  $rows += [pscustomobject]@{Name=$d;PreC=$pre.Count;PreB=$pre.Bytes;PostC=$post.Count;PostB=$post.Bytes;SrcLeft=$left;RC=$rc;Result=$res}
}
$frows = @()
foreach($f in $files){
  $s = Join-Path $src $f; $t = Join-Path $rdst $f
  if (-not (Test-Path -LiteralPath $s)) { L "FMISSING $f"; $frows += [pscustomobject]@{Name=$f;Pre='-';Post='-';Result='SOURCE MISSING'}; continue }
  if (Test-Path -LiteralPath $t) { L "FSKIP_DEST_EXISTS $f"; $frows += [pscustomobject]@{Name=$f;Pre=(Get-Item -LiteralPath $s).Length;Post='-';Result='SKIPPED dest exists'}; continue }
  $pl = (Get-Item -LiteralPath $s -Force).Length
  try { Move-Item -LiteralPath $s -Destination $t -ErrorAction Stop; $ql = (Get-Item -LiteralPath $t -Force).Length; $r = if (($ql -eq $pl) -and -not (Test-Path -LiteralPath $s)) {'OK'} else {'MISMATCH'} }
  catch { $ql = '-'; $r = 'FAILED: ' + $_.Exception.Message }
  L "FILE $f pre=$pl post=$ql $r"
  $frows += [pscustomobject]@{Name=$f;Pre=$pl;Post=$ql;Result=$r}
}
$md = @()
$md += '# MOVE-LOG: grok-bot-xfer -> xuanyi\legacy-xfer'
$md += ''
$md += "- Run: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') (Asia/Shanghai)"
$md += "- Source: $src"
$md += "- Dest: $dst (root files -> _root-files\)"
$md += '- Method: folders via robocopy /E /MOVE /COPY:DAT /DCOPY:T; root files via Move-Item. Nothing deleted outright.'
$md += '- Verify: file count + total bytes + per-file relative path|size list, before vs after.'
$md += ''
$md += '## Folders'
$md += ''
$md += '| Folder | Pre files | Pre bytes | Post files | Post bytes | Src left | robocopy rc | Result |'
$md += '|---|---|---|---|---|---|---|---|'
foreach($r in $rows){ $md += "| $($r.Name) | $($r.PreC) | $($r.PreB) | $($r.PostC) | $($r.PostB) | $($r.SrcLeft) | $($r.RC) | $($r.Result) |" }
$tc = ($rows | Where-Object { $_.PreC -is [int] } | Measure-Object PreC -Sum).Sum; $tb = ($rows | Where-Object { $_.PreB -is [int64] } | Measure-Object PreB -Sum).Sum
$pc = ($rows | Where-Object { $_.PostC -is [int] } | Measure-Object PostC -Sum).Sum; $pb = ($rows | Where-Object { $_.PostB -is [int64] } | Measure-Object PostB -Sum).Sum
$md += "| **TOTAL** | $tc | $tb | $pc | $pb | | | |"
$md += ''
$md += '## Root files -> _root-files\'
$md += ''
$md += '| File | Pre bytes | Post bytes | Result |'
$md += '|---|---|---|---|'
foreach($r in $frows){ $md += "| $($r.Name) | $($r.Pre) | $($r.Post) | $($r.Result) |" }
$fpb = ($frows | Where-Object { $_.Pre -is [int64] } | Measure-Object Pre -Sum).Sum; $fqb = ($frows | Where-Object { $_.Post -is [int64] } | Measure-Object Post -Sum).Sum
$md += "| **TOTAL $(@($frows | Where-Object {$_.Result -eq 'OK'}).Count)/$($frows.Count) OK** | $fpb | $fqb | |"
Set-Content -LiteralPath (Join-Path $dst 'MOVE-LOG.md') -Value $md -Encoding UTF8
L 'DONE'
