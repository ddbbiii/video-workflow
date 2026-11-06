$ErrorActionPreference = 'Continue'
$log = 'E:\program\1project\video\.cleanup\admin-result.txt'
Remove-Item $log -Force -ErrorAction SilentlyContinue

function Log([string]$m) {
    $line = "{0}  {1}" -f (Get-Date).ToString('HH:mm:ss'), $m
    Add-Content -LiteralPath $log -Value $line -Encoding UTF8
}

$d = New-Object System.IO.DriveInfo('C')
Log ("===== 开始 =====  C盘可用: {0:N2} GB" -f ($d.TotalFreeSpace / 1GB))

# ---- A1 关闭休眠 ----
Log "----- A1 休眠文件 -----"
$hb = Get-Item 'C:\hiberfil.sys' -Force -ErrorAction SilentlyContinue
if ($hb) { Log ("休眠文件大小: {0:N2} GB" -f ($hb.Length / 1GB)) } else { Log "休眠文件未找到（可能已关闭）" }
$out = & powercfg.exe /h off 2>&1
if ($out) { $out | ForEach-Object { Log "  powercfg: $_" } }
Start-Sleep -Seconds 2
if (Test-Path 'C:\hiberfil.sys') {
    Log "结果: hiberfil.sys 仍然存在（关闭失败）"
} else {
    Log "结果: hiberfil.sys 已删除"
}

# ---- A2 DISM 组件清理 ----
Log "----- A2 组件存储清理 (StartComponentCleanup，不加 ResetBase) -----"
$sw = [Diagnostics.Stopwatch]::StartNew()
& dism.exe /Online /Cleanup-Image /StartComponentCleanup 2>&1 | ForEach-Object {
    if ($_ -match '\S') { Log "  dism: $_" }
}
$sw.Stop()
Log ("DISM 耗时: {0:N1} 分钟" -f $sw.Elapsed.TotalMinutes)

# ---- A3 系统日志 ----
Log "----- A3 系统日志 -----"
$logPaths = @(
    'C:\Windows\Logs\CBS', 'C:\Windows\Logs\DISM', 'C:\Windows\Logs\WindowsUpdate',
    'C:\Windows\Logs\waasmedic', 'C:\Windows\Logs\NetSetup', 'C:\Windows\Logs\PITR',
    'C:\Windows\Logs\MeasuredBoot', 'C:\Windows\Panther'
)
$freed = 0L
foreach ($p in $logPaths) {
    if (Test-Path -LiteralPath $p) {
        $before = (Get-ChildItem -LiteralPath $p -Recurse -File -Force -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
        Get-ChildItem -LiteralPath $p -Recurse -File -Force -ErrorAction SilentlyContinue |
            Remove-Item -Force -ErrorAction SilentlyContinue
        $after = (Get-ChildItem -LiteralPath $p -Recurse -File -Force -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
        $freed += ($before - $after)
        Log ("  {0}: 清理 {1:N1} MB" -f $p, (($before - $after) / 1MB))
    }
}
Log ("日志清理合计: {0:N1} MB" -f ($freed / 1MB))

# ---- A4 还原点占用 ----
Log "----- A4 卷影/还原点占用 -----"
& vssadmin.exe list shadowstorage 2>&1 | ForEach-Object { if ($_ -match '\S') { Log "  vss: $_" } }

# ---- 汇总 ----
$d.Refresh()
Log ("===== 结束 =====  C盘可用: {0:N2} GB" -f ($d.TotalFreeSpace / 1GB))
Log "SCRIPT_DONE"
