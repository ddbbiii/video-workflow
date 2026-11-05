import json,time,hashlib
from pathlib import Path
import torch,soundfile as sf
from voxcpm import VoxCPM
ROOT=Path(r'E:\program\1project\video\assets\猎奇\voices')
MODEL=r'E:\program\1project\video\shared\runtime\engines\tts\voxcpm\pretrained_models\VoxCPM2'
ROLES={
'lieqi-tudou-tomato-heiress':[
 '土豆哥哥，我以前说话太重了，对不起。现在番茄家遇到麻烦，希望你能给我们一个机会。',
 '番茄家今天来了客人。土豆哥哥，好久不见。我承认当年的话很伤人，我们可以好好谈谈吗。'],
'lieqi-tudou-cucumber':[
 '我是黄瓜大少，冷链进口，天天冰镇，顶花带刺。现在冰箱断电了，我想找一份踏实的工作。',
 '先别急着笑，我是黄瓜大少。以前我自鸣得意，现在只想把事情做好，求您给我一个机会。'],
'lieqi-tudou-onion':[
 '总裁，番茄家到了。我没有哭，只是眼睛有点辣。番茄家的债务已经核对清楚，收购手续也准备好了。',
 '总裁，客人已经到了。我会把文件说明白，不会耽误您的时间。番茄家的土地已经收购，接下来请您安排。']}
CONFIGS=[('cfg15-s7-t20',1.5,20,7,0),('cfg25-s7-t20',2.5,20,7,0),('cfg15-s123-t30',1.5,30,123,1),('cfg25-s123-t30',2.5,30,123,1)]
print('START',time.strftime('%Y-%m-%dT%H:%M:%S%z'),flush=True)
m=VoxCPM.from_pretrained(MODEL,load_denoiser=False,optimize=False)
print('LOADED',m.tts_model.sample_rate,flush=True)
for aid,texts in ROLES.items():
 d=ROOT/aid; ref=d/'ref_audio.wav'; reftext=(d/'ref_text.txt').read_text(encoding='utf-8')
 for name,cfg,steps,seed,ti in CONFIGS:
  od=d/'_attempts'/name; od.mkdir(parents=True,exist_ok=True); text=texts[ti]
  torch.manual_seed(seed)
  if torch.cuda.is_available(): torch.cuda.manual_seed_all(seed); torch.cuda.synchronize()
  print('GENERATING',aid,name,flush=True); t=time.time(); w=m.generate(text=text,cfg_value=cfg,inference_timesteps=steps,reference_wav_path=str(ref),prompt_wav_path=str(ref),prompt_text=reftext); dt=time.time()-t
  sf.write(od/'sample.wav',w,m.tts_model.sample_rate,subtype='PCM_16')
  meta={'asset_id':aid,'attempt':name,'cfg_value':cfg,'inference_timesteps':steps,'seed':seed,'sample_text':text,'duration_s':round(len(w)/m.tts_model.sample_rate,3),'generation_s':round(dt,1),'reference':'ref_audio.wav','prompt_text':'ref_text.txt'}
  (od/'meta.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
  print('RESULT',json.dumps(meta,ensure_ascii=False),flush=True)
print('ALL_DONE',flush=True)
