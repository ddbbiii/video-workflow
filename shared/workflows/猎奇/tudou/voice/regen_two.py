import json, time
from pathlib import Path
import torch, soundfile as sf
from voxcpm import VoxCPM
ROOT=Path(r'E:\program\1project\video\assets\猎奇\voices')
MODEL=r'E:\program\1project\video\shared\runtime\engines\tts\voxcpm\pretrained_models\VoxCPM2'
TEXTS={
'lieqi-tudou-potato':'哭什么？今天是好日子。伯父，好久不见。我现在是金脆脆薯片集团总裁。重新开始？当年你让我滚回地里，我就在地里，一滚就是三年。',
'lieqi-tudou-tomato-dad':'谁啊，这么大排场……这，这不是土豆吗？你怎么削皮了？薯片？那个一年卖十个亿的金脆脆？'
}
print('START',time.strftime('%Y-%m-%dT%H:%M:%S%z'),flush=True)
m=VoxCPM.from_pretrained(MODEL,load_denoiser=False,optimize=False)
for aid,text in TEXTS.items():
 d=ROOT/aid; ref=d/'ref_audio.wav'; reftext=(d/'ref_text.txt').read_text(encoding='utf-8'); torch.manual_seed(42)
 if torch.cuda.is_available(): torch.cuda.manual_seed_all(42); torch.cuda.synchronize()
 print('GENERATING',aid,flush=True); w=m.generate(text=text,cfg_value=2.0,inference_timesteps=10,reference_wav_path=str(ref),prompt_wav_path=str(ref),prompt_text=reftext)
 sf.write(d/'sample_10s.wav',w,m.tts_model.sample_rate,subtype='PCM_16'); print('RESULT',aid,round(len(w)/m.tts_model.sample_rate,3),flush=True)
