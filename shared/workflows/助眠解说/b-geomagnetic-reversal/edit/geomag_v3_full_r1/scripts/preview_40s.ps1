# 40s preview: intro + junction + body head, BGM mix + narration + style_r4 burned subs. 2026-10-08 迁移后 cwd = 单集根。
$ErrorActionPreference='Stop'
$O='E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal'; Set-Location $O
$BODY='video\source\geomag_v3_body_r1.mp4'
$out='video\preview\geomag_full_r1_preview_40s.mp4'; if(Test-Path $out){throw "exists $out"}
$fc="[1:v]split=2[s1][s2];" +
 "[0:v]setsar=1,format=yuv420p,setpts=N/30/TB[a];" +
 "[s1]trim=end_frame=667,setsar=1,format=yuv420p,setpts=N/30/TB[b];" +
 "[2:v]setsar=1,format=yuv420p,setpts=N/30/TB[c];" +
 "[s2]trim=start_frame=854:end_frame=1300,setsar=1,format=yuv420p,setpts=N/30/TB[d];" +
 "[a][b][c][d]concat=n=4:v=1:a=0,trim=end_frame=1200,setpts=N/30/TB,subtitles=filename=audio/subtitles/full_r1/geomag_full_r1.ass:fontsdir=../../../../assets/助眠解说/subtitles/style-r4/fonts[v]"
ffmpeg -hide_banner -nostdin -n -i video\intro\full_r1_src\intro_video_r1.mkv -i $BODY -i video\clips\full_r1_c06b\region_c06b_r1.mkv -i audio\geomag_full_r1_full_mix.wav `
 -filter_complex $fc -map '[v]' -map 3:a -t 40 -r 30 -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p -profile:v high `
 -c:a aac -b:a 192k -ar 48000 -movflags +faststart $out 2>&1 | Out-File -Encoding utf8 logs\full_r1\preview_40s.log
ffprobe -v error -show_entries format=duration:stream=codec_name,width,height,nb_frames,sample_rate -of compact $out