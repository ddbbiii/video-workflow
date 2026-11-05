# 悬疑动漫《她变好了》VoxCPM2 配音 runner（ddbbi）。2026-10-02 悬疑动漫写。
# 做的事和 kepu-pipeline windows/voxcpm2/run_shots.ps1 一样（同样的环境变量、同一个已部署的 gen_shots.py，不改它），
# 另外按 docs/stills-plan.md 第 3 节的约定 **写** gpu.lock（run_shots.ps1 本身只读锁不写锁）：
#   1) 等待：gpu.lock 被别的活进程持有，或有别的 GPU 类 python 进程（TTS / ComfyUI / 放大 / i2v）在跑 -> 每 30 s 记一行 WAIT，不杀任何进程
#   2) 原子创建 gpu.lock：{"owner": "tts:xuanyi-mirror:<tag>", "pid": <本进程>, "started": ...}
#   3) 跑 gen_shots.py；4) finally：锁里的 pid 是自己才删锁
# 用法：powershell -NoProfile -ExecutionPolicy Bypass -File run_vo.ps1 -Jobs <jobs.json> -Tag <tag> -Log <log> [-MaxWaitMin 240]
param([Parameter(Mandatory=$true)][string]$Jobs, [Parameter(Mandatory=$true)][string]$Tag,
      [Parameter(Mandatory=$true)][string]$Log, [int]$MaxWaitMin = 240)
$ErrorActionPreference = "Continue"
$env:HF_ENDPOINT = "https://hf-mirror.com"
$env:PYTHONIOENCODING = "utf-8"
$env:MODELSCOPE_CACHE = "E:\program\1project\video\shared\runtime\engines\tts\modelscope-cache"
$env:HF_HOME = "E:\program\1project\video\shared\runtime\engines\tts\hf-cache"
$lock = "E:\program\1project\video\shared\work\cache\gpu.lock"
$owner = "tts:xuanyi-mirror:$Tag"
function L($m) { "$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss')) $m" | Out-File -FilePath $Log -Append -Encoding utf8 }
function Busy {
  if (Test-Path $lock) {
    try { $l = Get-Content $lock -Raw | ConvertFrom-Json } catch { return "gpu.lock unreadable (treating as held)" }
    if ($l.pid -and (Get-Process -Id $l.pid -ErrorAction SilentlyContinue)) { return "gpu.lock held by $($l.owner) pid $($l.pid) since $($l.started)" }
    return $null   # stale lock (pid gone) -> takeover allowed, same rule as run_stills.py
  }
  $p = Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python' -and $_.ProcessId -ne $PID -and $_.CommandLine -match 'shared\runtime\engines\tts|voxcpm|index-tts|gen_shots|ComfyUI|comfy|main\.py|upscale|esrgan|i2v|ltx|wan|hunyuan' }
  if ($p) { return "gpu python process(es): " + (($p | ForEach-Object { "$($_.ProcessId)" }) -join ",") }
  return $null
}
L "=== RUNNER $owner pid $PID jobs=$Jobs"
$t0 = Get-Date
while ($true) {
  $b = Busy
  if (-not $b) {
    if (Test-Path $lock) { L "stale gpu.lock -> taking over"; Remove-Item $lock -Force -ErrorAction SilentlyContinue }
    try {
      $fs = [System.IO.File]::Open($lock, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write)
      $txt = (@{ owner = $owner; pid = $PID; started = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz") } | ConvertTo-Json -Compress)
      $bytes = [System.Text.Encoding]::UTF8.GetBytes($txt); $fs.Write($bytes, 0, $bytes.Length); $fs.Close()
      break
    } catch { $b = "lost race creating gpu.lock" }
  }
  if (((Get-Date) - $t0).TotalMinutes -gt $MaxWaitMin) { L "TIMEOUT waiting for GPU ($b) -> not running"; L "=== END exit=99"; exit 99 }
  L "WAIT $b"
  Start-Sleep 30
}
L "gpu.lock acquired (waited $([int]((Get-Date) - $t0).TotalSeconds)s)"
$code = 1
try {
  Set-Location E:\program\1project\video\shared\runtime\engines\tts\voxcpm
  L "=== START jobs=$Jobs"
  & .venv\Scripts\python.exe gen_shots.py $Jobs 2>&1 | ForEach-Object { "$_" } | Out-File -FilePath $Log -Append -Encoding utf8
  $code = $LASTEXITCODE
} finally {
  try { $l = Get-Content $lock -Raw | ConvertFrom-Json; if ($l.pid -eq $PID) { Remove-Item $lock -Force; L "gpu.lock released" } else { L "gpu.lock not mine (pid $($l.pid)), left as is" } } catch { L "gpu.lock already gone" }
  L "=== END exit=$code"
}
