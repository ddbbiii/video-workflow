$ErrorActionPreference='Continue'
$env:PYTHONUTF8='1'
& 'E:\program\1project\video\shared\runtime\comfy\installs\portable\python_embeded\python.exe' -u 'E:\program\1project\video\shared\project-tools\lora\charb-jacket-v1\expand_charb_jacket_img2img.py' *>> 'E:\program\1project\video\xfer\charb-jacket-prep\expand-run.log'
Add-Content 'E:\program\1project\video\xfer\charb-jacket-prep\expand-run.log' "EXIT $LASTEXITCODE $(Get-Date -Format o)"
