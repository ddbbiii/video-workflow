from pathlib import Path
import subprocess,json,re
root=Path(__file__).resolve().parents[1]
video=root/'video/小球_300层_向下重力240.mp4'
output=json.loads((root/'simulation/trace.json').read_text())['output']
probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(video)]))
v=next(s for s in probe['streams'] if s['codec_type']=='video');a=next(s for s in probe['streams'] if s['codec_type']=='audio')
assert len(probe['streams'])==2
assert (v['width'],v['height'],v['r_frame_rate'],int(v['nb_frames']))==(1080,1920,'60/1',output['frames'])
assert abs(float(v['duration'])-output['duration'])<1/60
assert abs(float(a['duration'])-output['duration'])<.05
p=subprocess.run(['ffmpeg','-hide_banner','-i',str(video),'-vf','blackdetect=d=1:pix_th=.05,freezedetect=n=-60dB:d=1','-af','ebur128=peak=true','-f','null','-'],capture_output=True,text=True)
(root/'qa/decode.txt').write_text(p.stderr)
assert p.returncode==0
black=re.findall(r'black_start:[^\n]+',p.stderr);freeze=re.findall(r'freeze_start[^\n]+',p.stderr)
assert not black and not freeze
summary=p.stderr[p.stderr.rfind('Summary:'):]
peak=float(re.search(r'Peak:\s*([\-\d.]+) dBFS',summary).group(1))
assert peak<=-1
report={'streams':probe['streams'],'duration':probe['format']['duration'],'full_decode_passed':True,'black_events':black,'freeze_events':freeze,'loudness_summary':summary,'aac_true_peak_dbfs':peak}
(root/'qa/media.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({'duration':probe['format']['duration'],'peak':peak,'decode':True,'black':black,'freeze':freeze},ensure_ascii=False))
subprocess.run(['ffmpeg','-v','error','-y','-i',str(video),'-vf','fps=1/15,scale=216:384,tile=4x3','-frames:v','1',str(root/'qa/contact.jpg')],check=True)
