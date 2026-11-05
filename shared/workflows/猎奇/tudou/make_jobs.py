import json
from pathlib import Path
src=Path(r'E:\program\1project\video\projects\猎奇\episodes\tudou\storyboard\shotlist_v1.json')
d=json.loads(src.read_text(encoding='utf-8'))
R={
'lieqi-tudou-potato': (r'E:\program\1project\video\shared\runtime\engines\tts\refs\lieqi-tudou-potato_ref.wav','小红，我们不是从小一个菜园子长大的吗？你说过不嫌弃我的。伯父，我虽然土，但我实在，煎炒烹炸样样都行。你是谁？好。今日之辱，我记下了。三年之后，我让你们番茄家高攀不起！',1.5,20,7,[168.4,238.2]),
'lieqi-tudou-tomato-heiress': (r'E:\program\1project\video\shared\runtime\engines\tts\refs\lieqi-tudou-tomato-heiress_ref.wav','土豆，这婚我退了！你看看你，浑身是泥，还发芽，丢不丢人！那是小时候！现在我是番茄家千金，要上米其林沙拉的！还是黄瓜哥哥清爽。土豆，滚回你的地里去吧！',1.5,20,7,[246.1,348.1]),
'lieqi-tudou-cucumber': (r'E:\program\1project\video\shared\runtime\engines\tts\refs\lieqi-tudou-cucumber_ref.wav','哟，这就是那颗土豆啊？浑身疙瘩，比我还丑。我？黄瓜大少，冷链进口，天天冰镇，顶花带刺！小红，以后跟我。别提了，冰箱断电，我都快蔫了。求您给口饭吃！',1.5,20,7,[263.6,372.8]),
'lieqi-tudou-tomato-dad': (r'E:\program\1project\video\shared\runtime\engines\tts\refs\lieqi-tudou-tomato-dad_ref.wav','听见没？我们番茄家，红得发亮！你一个埋土里的，配吗？土就是土！这是你家给的彩礼？两袋化肥？拿回去！谁啊，这么大排场……这，这不是土豆吗？你怎么削皮了？',1.5,20,7,[136.1,192.5]),
'lieqi-tudou-onion': (r'E:\program\1project\video\shared\runtime\engines\tts\refs\lieqi-tudou-onion_ref.wav','总裁，番茄家到了。呜……我没哭，是我自己辣眼睛。没错。番茄家欠了一屁股债，这块地，我们总裁已经收购了。黄瓜味薯片，上线！',1.5,30,123,[228.2,322.8])}
items=[]
for s in d['shots']:
 if s.get('voice') and s.get('text'):
  ref,prompt,cfg,steps,seed,band=R[s['voice']]
  items.append({'id':s['id'],'text':s['text'],'voice':s['voice'],'desc_in_text':False,'reference_wav':ref,'prompt_wav':ref,'prompt_text':prompt,'cfg_value':cfg,'inference_timesteps':steps,'seed':seed,'vo_gate_pitch_band_hz':band})
out={'out_dir':r'E:\program\1project\video\projects\猎奇\episodes\tudou\archive\audio\voxcpm2-shots','model_dir':r'E:\program\1project\video\shared\runtime\engines\tts\voxcpm\pretrained_models\VoxCPM2','desc':'','desc_in_text':False,'cfg_value':2.0,'inference_timesteps':10,'seed':7,'reference_wav':None,'prompt_wav':None,'prompt_text':None,'mode':'ultimate','shots':items}
Path(r'E:\program\1project\video\shared\workflows\猎奇\tudou\voice\voxcpm2_jobs.json').write_text(json.dumps(out,ensure_ascii=False,indent=1),encoding='utf-8')
print('WROTE',len(items))