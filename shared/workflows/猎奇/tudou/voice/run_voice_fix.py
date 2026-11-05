import json,time
from pathlib import Path
import torch,soundfile as sf
from voxcpm import VoxCPM
ROOT=Path(r'E:\program\1project\video\assets\猎奇\voices');MODEL=r'E:\program\1project\video\shared\runtime\engines\tts\voxcpm\pretrained_models\VoxCPM2'
items={
'lieqi-tudou-potato':'哭什么？今天是好日子。伯父，好久不见。我现在是金脆脆薯片集团总裁。重新开始？当年你让我滚回地里，我就在地里，一滚就是三年。',
'lieqi-tudou-tomato-dad':'谁啊，这么大排场……这，这不是土豆吗？你怎么削皮了？薯片？那个一年卖十个亿的金脆脆？听见没？我们番茄家，红得发亮！'}
m=VoxCPM.from_pretrained(MODEL,load_denoiser=False,optimize=False)
for aid,text in items.items():
 d=ROOT/aid; name='cfg15-s7-t20-fix';od=d/'_attempts'/name;od.mkdir(parents=True,exist_ok=True);ref=d/'ref_audio.wav';rt=(d/'ref_text.txt').read_text(encoding='utf-8');torch.manual_seed(7)
 if torch.cuda.is_available():torch.cuda.manual_seed_all(7);torch.cuda.synchronize()
 w=m.generate(text=text,cfg_value=1.5,inference_timesteps=20,reference_wav_path=str(ref),prompt_wav_path=str(ref),prompt_text=rt);sf.write(od/'sample.wav',w,m.tts_model.sample_rate,subtype='PCM_16');meta={'asset_id':aid,'attempt':name,'cfg_value':1.5,'inference_timesteps':20,'seed':7,'sample_text':text,'duration_s':round(len(w)/m.tts_model.sample_rate,3)}; (od/'meta.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(meta,ensure_ascii=False),flush=True)
