$ErrorActionPreference = "Stop"
$python = "E:\\program\\1project\\video\\shared\\runtime\\comfy\\installs\\portable\\python_embeded\\python.exe"
$script = Join-Path $PSScriptRoot "run_vsr_streaming.py"
$env:VSR_OUTPUT_DIR = "E:\\program\\1project\\video\\projects\\助眠解说\\legacy-source\\zhumian\\b-geomagnetic-reversal\\gen_rebuild\\runs\\20261007-vsr-baseline-c04-streaming-retry4"
& $python $script
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
