@echo off
cd /d E:\program\1project\video\shared\runtime\comfy\installs\portable
if exist run_nvidia_gpu.bat (
  call run_nvidia_gpu.bat
) else if exist ComfyUI\main.py (
  python_embeded\python.exe ComfyUI\main.py --listen 127.0.0.1 --port 8188
) else (
  echo No known Portable launcher found.
  pause
)
