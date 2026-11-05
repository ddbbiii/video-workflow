$ErrorActionPreference='Continue'
Add-Content 'E:\program\1project\video\xfer\charb-jacket-prep\train-run.log' "TRAIN_START $(Get-Date -Format o)"
powershell -NoProfile -ExecutionPolicy Bypass -File 'E:\program\1project\video\shared\project-tools\lora\charb-jacket-v1\train-charb-jacket-v1.ps1' *>> 'E:\program\1project\video\xfer\charb-jacket-prep\train-run.log'
Add-Content 'E:\program\1project\video\xfer\charb-jacket-prep\train-run.log' "TRAIN_EXIT $LASTEXITCODE $(Get-Date -Format o)"
