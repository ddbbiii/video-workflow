import os, json, time, shutil, hashlib, math, traceback
from pathlib import Path
import numpy as np
import soundfile as sf
import torch
from voxcpm import VoxCPM

ROOT = Path(r'E:\program\1project\video\projects\猎奇\episodes\tudou')
CAND = ROOT / 'archive' / 'audio' / 'voice-candidates'
FINAL = Path(r'E:\program\1project\video\assets\猎奇\voices')
MODEL = Path(r'E:\program\1project\video\shared\runtime\engines\tts\voxcpm\pretrained_models\VoxCPM2')
SR = 48000
CFG = 2.0
STEPS = 10
ROLES = [
 {'id':'lieqi-tudou-potato','role':'potato','label':'土豆小伙','file':'potato_42.wav','desc':'20岁出头的年轻男性，诚实、委屈，正常语速，句尾干净利落不拖不压，没有气泡音和沙哑感','ref_text':'小红，我们不是从小一个菜园子长大的吗？你说过不嫌弃我的。伯父，我虽然土，但我实在，煎炒烹炸样样都行。你是谁？好。今日之辱，我记下了。三年之后，我让你们番茄家高攀不起！','sample_text':'哭什么？今天是好日子。伯父，好久不见。我现在是金脆脆薯片集团总裁。重新开始？当年你让我滚回地里，我就在地里，一滚就是三年。不必了，我现在只吃原味。秘书，送客。正好，生产线缺一款新口味。记住，莫欺少年穷，莫欺土豆没削皮。'},
 {'id':'lieqi-tudou-tomato-heiress','role':'tomato-heiress','label':'番茄千金','file':'tomato-heiress_42.wav','desc':'20多岁的女性，尖刻、嚣张、阴阳怪气，语速快但不尖细，句尾干净利落不拖不压，没有气泡音和沙哑感','ref_text':'土豆，这婚我退了！你看看你，浑身是泥，还发芽，丢不丢人！那是小时候！现在我是番茄家千金，要上米其林沙拉的！还是黄瓜哥哥清爽。土豆，滚回你的地里去吧！','sample_text':'土豆哥哥！我错了！我当年是被黄瓜骗了！我们重新开始好不好？那……那我给你当番茄酱，以后天天陪你蘸薯片，行吗？'},
 {'id':'lieqi-tudou-cucumber','role':'cucumber','label':'黄瓜大少','file':'cucumber_42.wav','desc':'20多岁的男性，油腻、自鸣得意、轻佻有玩笑感，语速快，音高和土豆明显不同，句尾干净利落不拖不压，没有气泡音和沙哑感','ref_text':'哟，这就是那颗土豆啊？浑身疙瘩，比我还丑。我？黄瓜大少，冷链进口，天天冰镇，顶花带刺！小红，以后跟我。别提了，冰箱断电，我都快蔫了。求您给口饭吃！','sample_text':'哟，这就是那颗土豆啊？浑身疙瘩，比我还丑。我？黄瓜大少，冷链进口，天天冰镇，顶花带刺！小红，以后跟我。别提了，冰箱断电，我都快蔫了。求您给口饭吃！'},
 {'id':'lieqi-tudou-tomato-dad','role':'tomato-dad','label':'番茄老爹','file':'tomato-dad_42.wav','desc':'50岁左右的男性，中低音，暴发户拖腔，势利、摆谱，句尾干净利落不拖不压，没有气泡音和沙哑感','ref_text':'听见没？我们番茄家，红得发亮！你一个埋土里的，配吗？土就是土！这是你家给的彩礼？两袋化肥？拿回去！谁啊，这么大排场……这，这不是土豆吗？你怎么削皮了？','sample_text':'听见没？我们番茄家，红得发亮！你一个埋土里的，配吗？土就是土！这是你家给的彩礼？两袋化肥？拿回去！谁啊，这么大排场……这，这不是土豆吗？你怎么削皮了？薯片？那个一年卖十个亿的金脆脆？'},
 {'id':'lieqi-tudou-onion','role':'onion-secretary','label':'洋葱秘书','file':'onion-secretary_42.wav','desc':'20多岁的女性，始终带着哭腔，抽抽搭搭但每个音节清晰，句尾干净利落不拖不压，没有气泡音和沙哑感','ref_text':'总裁，番茄家到了。呜……我没哭，是我自己辣眼睛。没错。番茄家欠了一屁股债，这块地，我们总裁已经收购了。黄瓜味薯片，上线！','sample_text':'总裁，番茄家到了。呜……我没哭，是我自己辣眼睛。没错。番茄家欠了一屁股债，这块地，我们总裁已经收购了。黄瓜味薯片，上线！'},
]

def md5(p):
 h=hashlib.md5()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()

def median_f0(path):
 y,sr=sf.read(path,dtype='float32')
 if y.ndim>1: y=y.mean(1)
 frame=max(256,int(sr*.04)); hop=max(128,int(sr*.01)); lo=max(1,int(sr/500)); hi=min(frame-2,int(sr/70)); vals=[]
 for st in range(0,max(0,len(y)-frame+1),hop):
  x=y[st:st+frame].astype(np.float64); x-=x.mean(); rms=math.sqrt(float(np.mean(x*x)))
  if rms<.004: continue
  x*=np.hamming(frame); ac=np.correlate(x,x,mode='full')[frame-1:]
  if ac[0]<=1e-10: continue
  lag=lo+int(np.argmax(ac[lo:hi+1])); peak=float(ac[lag]/ac[0])
  if peak<.28: continue
  delta=0.0
  if 1<=lag<len(ac)-1:
   a,b,c=float(ac[lag-1]),float(ac[lag]),float(ac[lag+1]); den=a-2*b+c
   if abs(den)>1e-12: delta=max(-.5,min(.5,.5*(a-c)/den))
  f=sr/(lag+delta)
  if 70<=f<=500: vals.append(f)
 return round(float(np.median(vals)),1) if vals else None

print('START', time.strftime('%Y-%m-%dT%H:%M:%S%z'), flush=True)
FINAL.mkdir(parents=True,exist_ok=True)
print('LOADING', MODEL, flush=True)
model=VoxCPM.from_pretrained(str(MODEL),load_denoiser=False,optimize=False)
print('LOADED', model.tts_model.sample_rate, torch.__version__, torch.cuda.is_available(), flush=True)
records=[]
for r in ROLES:
 d=FINAL/r['id']; d.mkdir(parents=True,exist_ok=True); (d/'refs').mkdir(exist_ok=True)
 src=CAND/r['file']; ref=d/'ref_audio.wav'; shutil.copy2(src,ref); shutil.copy2(src,d/'refs'/(r['id']+'_ref.wav'))
 (d/'ref_text.txt').write_text(r['ref_text'],encoding='utf-8')
 torch.manual_seed(42)
 if torch.cuda.is_available(): torch.cuda.manual_seed_all(42); torch.cuda.synchronize()
 print('GENERATING',r['id'],flush=True)
 wav=model.generate(text=r['sample_text'],cfg_value=CFG,inference_timesteps=STEPS,reference_wav_path=str(ref),prompt_wav_path=str(ref),prompt_text=r['ref_text'])
 sample=d/'sample_10s.wav'; sf.write(sample,wav,model.tts_model.sample_rate,subtype='PCM_16')
 rec={'asset_id':r['id'],'role':r['role'],'label':r['label'],'reference_md5':md5(ref),'reference_bytes':ref.stat().st_size,'sample_seconds':round(len(wav)/model.tts_model.sample_rate,3),'sample_f0_median_hz':median_f0(sample),'sample_text':r['sample_text']}
 params={'asset_id':r['id'],'name':r['label'],'role':r['role'],'engine':'VoxCPM2','mode':'ultimate_clone','reference_audio':{'file':'ref_audio.wav','source':str(src),'description':'seed-42 candidate; byte-copied unchanged','md5':rec['reference_md5']},'prompt_audio':'ref_audio.wav','transcript_file':'ref_text.txt','transcript':r['ref_text'],'description':r['desc'],'cfg_value':CFG,'inference_timesteps':STEPS,'seed':42,'optimize':False,'denoiser':False,'normalize':False,'sample_rate':int(model.tts_model.sample_rate),'torch_manual_seed_before_take':True,'sample_text_file':'(documented in NOTES.md)','qa':{'f0_method':'lightweight autocorrelation median over voiced frames (same candidate generator method)','f0_median_hz':rec['sample_f0_median_hz'],'vo_gate_pitch_band_semitones':'±3'},'generation':rec,'ddbbi':{'candidate_path':str(src),'package_path':str(d)}}
 (d/'params.json').write_text(json.dumps(params,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 (d/'README.md').write_text(f"# {r['label']}（{r['id']}）\n\n- 状态：待登记；本目录为老大选定的 seed-42 声线包，未写入 registry。\n- 固定参考：`ref_audio.wav`（候选 `{r['file']}`，md5 `{rec['reference_md5']}`）。\n- 锁定逐字稿：`ref_text.txt`。\n- VoxCPM2 ultimate clone 试听：`sample_10s.wav`。\n- 参数和指标：`params.json`；说明：`NOTES.md`。\n",encoding='utf-8')
 risk = '持续哭腔可能出现破音或 F0 偏高' if r['role']=='onion-secretary' else ('男性角色可能出现偏高 F0；需听检低沉感和句尾' if r['role'] in ('potato','cucumber','tomato-dad') else '女性高音/尖刻情绪可能使 F0 偏高；需听检句尾')
 note=f"# {r['label']}（{r['id']}）声线包\n\n- 状态：待登记（本次不登记）。\n- 角色：{r['label']}（`{r['role']}`）。\n- 音色描述：{r['desc']}。\n- 设计来源：VoxCPM2 voice-design candidate seed 42；固定参考音为候选 `{r['file']}`，逐字稿锁定在 `ref_text.txt`，逐字一致。\n- 参考音 md5：`{rec['reference_md5']}`（{rec['reference_bytes']} bytes；`ref_audio.wav` 为字节复制）。\n- 续写模式：ultimate clone；reference/prompt wav 均为 `ref_audio.wav`，prompt text 为 `ref_text.txt`。\n- 参数：cfg_value=2.0，inference_timesteps=10，seed=42，optimize=False，denoiser=False，normalize=False，sample_rate=48000 Hz。\n- 试听文本（取剧本该角色台词；跳过黄瓜尖叫）：{r['sample_text']}\n- sample_10s.wav：{rec['sample_seconds']} s；轻量自相关 F0 中位数：{rec['sample_f0_median_hz']} Hz。\n- CAM++ speaker similarity：待在 box 上以对应参考音计算。\n- 建议 vo_gate：参考 F0 ±3 半音；待 QA 用参考 F0 换算 Hz 后写入登记。\n- 已知风险：{risk}。\n"
 (d/'NOTES.md').write_text(note,encoding='utf-8')
 records.append(rec); print('RESULT',json.dumps(rec,ensure_ascii=False),flush=True)
# pending discard list: exactly seeds 7 and 123
entries=[]; k=1
for r in ROLES:
 for seed in (7,123):
  p=CAND/(r['role']+'_'+str(seed)+'.wav'); n=p.stat().st_size
  entries.append({'id':f'LQTD{k:03d}','path':str(p),'machine':'ddbbi','file_count':1,'size_bytes':n,'size':f'{n/1048576:.2f} MB','category':'音频候选','reason':f"{r['label']} seed {seed}，未选用；老大选定 seed 42，待声线登记 owner 合并",'date_discarded':'2026-10-01','line':'土豆退婚流','status':'pending_delete','needs_confirm':False}); k+=1
lines=['schema: discards-v1',"updated: '2026-10-01'",'rules:','- 仅列入本文件的候选可由 owner 后续合并；本次不删除任何文件。','- 任何删除都要老大逐批确认（OK）后才执行；执行后把 status 改成 deleted，并在 note 里记删除日期。','- needs_confirm: true（需确认）的条目在确认前视同不可删。','entries:']
import yaml
(Path(r'E:\program\1project\video\projects\猎奇\episodes\tudou\logs\voice\discards_pending.yaml')).write_text(yaml.safe_dump(entries,allow_unicode=True,sort_keys=False),encoding='utf-8')
(Path(r'E:\program\1project\video\assets\猎奇\voices\generation_summary.json')).write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('ALL_DONE',json.dumps(records,ensure_ascii=False),flush=True)

