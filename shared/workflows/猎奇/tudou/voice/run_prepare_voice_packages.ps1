$ErrorActionPreference = 'Stop'
$env:HF_ENDPOINT = 'https://hf-mirror.com'
$env:PYTHONIOENCODING = 'utf-8'
$env:MODELSCOPE_CACHE = 'E:\program\1project\video\shared\runtime\engines\tts\modelscope-cache'
$env:HF_HOME = 'E:\program\1project\video\shared\runtime\engines\tts\hf-cache'
Set-Location 'E:\program\1project\video\shared\runtime\engines\tts\voxcpm'
& '.venv\Scripts\python.exe' 'E:\program\1project\video\shared\workflows\猎奇\tudou\voice\prepare_voice_packages.py'
exit $LASTEXITCODE
