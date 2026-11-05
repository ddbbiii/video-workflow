$B='E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\audio\vo-raw\ch1_A_v4'
foreach($s in 7,11,23,42){ & 'E:\program\1project\video\shared\runtime\engines\tts\voxcpm\run_shots.ps1' -Jobs "$B\jobs\jobs_seed$s.json" -Log "$B\logs\tts-seed$s.log" }
