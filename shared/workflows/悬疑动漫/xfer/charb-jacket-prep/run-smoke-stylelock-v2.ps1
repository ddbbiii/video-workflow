$env:PYTHONUTF8='1'
& 'E:\program\1project\video\shared\runtime\comfy\installs\portable\python_embeded\python.exe' -u 'E:\program\1project\video\shared\project-tools\lora\charb-jacket-v1\smoke_charb_jacket_stylelock_v2.py' *>> 'E:\program\1project\video\xfer\charb-jacket-prep\smoke-stylelock-v2.log'
Add-Content 'E:\program\1project\video\xfer\charb-jacket-prep\smoke-stylelock-v2.log' "EXIT $LASTEXITCODE $(Get-Date -Format o)"
