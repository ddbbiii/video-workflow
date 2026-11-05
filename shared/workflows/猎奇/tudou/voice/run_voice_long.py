import json,time
from pathlib import Path
import torch,soundfile as sf
from voxcpm import VoxCPM
ROOT=Path(r'E:\program\1project\video\assets\猎奇\voices'); MODEL=r'E:\program\1project\video\shared\runtime\engines\tts\voxcpm\pretrained_models\VoxCPM2'
items={
'lieqi-tudou-tomato-heiress':'土豆哥哥，我以前说话太重了，对不起。现在番茄家遇到麻烦，希望你能给我们一个机会。今天番茄家来了客人，我们可以坐下来好好谈谈。',
'lieqi-tudou-cucumber':'我是黄瓜大少，冷链进口，天天冰镇，顶花带刺。现在冰箱断电了，我想找一份踏实的工作。以前我自鸣得意，现在只想把事情做好。'}
m=VoxCPM.from_pretrained(MODEL,load_denoiser=False,optimize=False)
for aid,text in items.items():
 d=ROOT/aid; od=d/'_attempts'/'cfg15-s7-t20-long'; od.mkdir(parents=True,exist_ok=True); ref=d/'ref_audio.wav'; rt=(d/'ref_text.txt').read_text(encoding='utf-8'); torch.manual_seed(7)
 if torch.cuda.is_available(): torch.cuda.manual_seed_all(7); torch.cuda.synchronize()
 w=m.generate(text=text,cfg_value=1.5,inference_timesteps=20,reference_wav_path=str(ref),prompt_wav_path=str(ref),prompt_text=rt); sf.write(od/'sample.wav',w,m.tts_model.sample_rate,subtype='PCM_16')
 meta={'asset_id':aid,'attempt':'cfg15-s7-t20-long','cfg_value':1.5,'inference_timesteps':20,'seed':7,'sample_text':text,'duration_s':round(len(w)/m.tts_model.sample_rate,3)}; (od/'meta.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(json.dumps(meta,ensure_ascii=False),flush=True)
