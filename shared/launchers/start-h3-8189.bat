@echo off
set ROOT=E:\program\1project\video\shared\runtime\comfy\installs
"%ROOT%\portable\python_embeded\python.exe" "%ROOT%\h3-runtime\launch_h3.py" --listen 127.0.0.1 --port 8189 --input-directory "%ROOT%\h3-runtime\input" --output-directory "%ROOT%\h3-runtime\output" --temp-directory "%ROOT%\h3-runtime\temp" --user-directory "%ROOT%\h3-runtime\user" --disable-pinned-memory
