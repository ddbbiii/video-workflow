"""Text-only, deterministic handoff builder. Never starts media generation."""
import argparse, hashlib, json, math, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parent
WORK = ROOT.parents[3]
def save(path, data):
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--body-seconds', type=float)
    ap.add_argument('--intro-seconds', type=float, default=20)
    args = ap.parse_args()
    source = ROOT / 'story/NARRATION_MASTER.md'
    text = source.read_text(encoding='utf-8')
    sha = hashlib.sha256(source.read_bytes()).hexdigest()
    sections = re.findall(r'## \[(.*?)\][^\n]*\n(.*?)(?=\n## |\Z)', text, re.S)
    paragraphs, utterances = [], []
    for sec, body in sections:
        for n, para in enumerate(re.split(r'\n\s*\n', body.strip()), 1):
            para = para.replace('\n', '')
            pid = f'{sec}-p{n:02}'
            sentences = re.findall(r'[^。！？]+[。！？]?', para)
            chunks, chunk = [], ''
            for sentence in sentences:
                if chunk and len(chunk + sentence) > 110:
                    chunks.append(chunk); chunk = ''
                chunk += sentence
            if chunk: chunks.append(chunk)
            ids = []
            for k, chunk in enumerate(chunks, 1):
                uid = f'{pid}-u{k:02}'
                ids.append(uid)
                utterances.append(dict(id=uid, paragraph_id=pid, section=sec, text=chunk,
                                       runnable='【' not in chunk))
            assert ''.join(chunks) == para
            paragraphs.append(dict(id=pid, section=sec, text=para, utterance_ids=ids))
    save('audio/utterances.json', dict(source_sha256=sha, paragraphs=paragraphs, utterances=utterances))
    config = dict(out_dir=str(ROOT / 'audio/vo-raw/seed7'),
                  model_dir=str(WORK / 'shared/runtime/engines/tts/voxcpm/pretrained_models/VoxCPM2'),
                  seed=7, mode='ultimate', inference_timesteps=10, desc='', cfg_value=2,
                  reference_wav=str(WORK / 'shared/runtime/engines/tts/refs/b2-warm-male_ref.wav'),
                  prompt_wav=str(WORK / 'shared/runtime/engines/tts/refs/b2-warm-male_ref.wav'),
                  prompt_text='发电机就在外核。液态铁被热量推着翻滚，切过磁场，生出电流，电流又生出磁场。地面上的罗盘，感受到的就是这股磁场。它藏在很深的地下，安安静静，日夜不息。',
                  desc_in_text=False)
    for sec, _ in sections:
        shots = [dict(id=u['id'], text=u['text']) for u in utterances if u['section']==sec and u['runnable']]
        save(f'audio/jobs/{sec}.json', dict(config, shots=shots))
        save(f'audio/gate/{sec}-shotlist.json', dict(title='你是一只蟑螂', profile='b-sleep', language='zh', shots=shots))
    if args.body_seconds is not None:
        if args.body_seconds < 2400 or args.intro_seconds <= 0:
            raise ValueError('需要真实正文时长 >=2400s，片头估计时长必须 >0；不足40分钟先检查漏稿，不能填充静音')
        minute = math.floor((args.body_seconds + args.intro_seconds) / 60 + .5)
        u = next(u for u in utterances if '【' in u['text'])
        resolved = u['text'].replace('【实测整分钟】', str(minute))
        save('audio/jobs/intro-minute-resolved.json', dict(config, shots=[dict(id=u['id'], text=resolved)]))
        save('audio/intro-minute-resolution.json', dict(body_seconds=args.body_seconds, intro_seconds=args.intro_seconds,
                                                      minute=minute, text=resolved, source_sha256=sha,
                                                      status='provisional_until_actual_intro_measured'))
    # Each entry names a real scene, rather than drawing an explanatory slide.
    scenes = {
      'bridge':['远古森林地面，落叶与腐木之间的一小片庇护所'],
      'ch01':['落叶下的幼小蟑螂，触角前方一颗水珠','树皮路面与倒木入口，沙粒叶脉组成微型山谷','腐木旁啃食柔软植物碎屑','阴影中多种自然植物碎片形成食物来源','开阔叶面上的蟑螂，远处不清晰的捕食者轮廓','空地树枝与覆盖的阴影，随后空无一虫的安静落叶','另一处倒木阴影中的新个体，安全退路就在身后','藏身入口和附近食物处在同一真实空间','落叶树皮腐木形成多层森林地面，土壤细节丰富','自然石面上的模糊古昆虫化石印痕，不复原确定物种','倒木下的蟑螂，前方触角与潮湿夜景'],
      'ch02':['月光下林地，蟑螂沿暗处出行','触角接触植物纤维，保留完整身体','蟑螂停在树皮缝隙入口，探查边缘','碎屑气味来源附近，蟑螂转向而不画气味线','后方叶片被轻风扰动，蟑螂完整侧后轮廓','逃生路线有树枝障碍，蟑螂安全停靠','树皮内部安静的蟑螂，外面脚步只有柔和影子','同一林地内两个略有不同的个体，各自觅食','一道温和月光穿过树叶，虫体回到阴影','狭窄树皮缝隙入口，身体伏低准备进入'],
      'ch03':['扁平蟑螂俯视完整轮廓，天然叶面背景','蟑螂已位于低矮裂缝内，不展示极端挤压','完整六足蟑螂站在粗糙树皮与湿叶交界','狭缝深处小虫与入口外遥远轮廓','略干燥缝隙旁的水珠堵住另一个小入口','自然外骨骼柔和光泽，完整中景而非装甲','小虫与巨大叶片形成尺度关系，不做人形巨虫','两只蟑螂分开停在同一藏身地，不做虫群','成长后的若虫在原有略狭小的树皮房间'],
      'ch04':['蜕皮前若虫安静藏在树皮下','蜕皮后的浅色若虫与一具空旧壳分开静置','柔软浅色若虫安静等待，外面食物遥远','恢复正常色泽的若虫重新站稳，使用不同静帧','单只若虫的完整轮廓，不出现毛虫蛹','有完整覆翅的野生蟑螂静停在叶片上','有翅成虫已经停靠在另一片树皮，不生成变翼','成虫与碎裂腐木，环境比此前更疏松'],
      'ch05':['干旱落叶边缘卷曲，虫体停在阴影','倒木底部深色湿土成为避难角落','干燥木屑旁少量柔软植物碎片','干枯空树皮房间，生命离开但不展示尸体','另一个湿润森林角落中的新个体','两个环境中相似但有细小差异的蟑螂分别单独成景','不同森林植被场景，各自独立不用年代图表','微型森林地面，远方大型动物仅模糊剪影','受环境变化影响的空旷林地，不用灾难爆炸','新落叶下稳定生活的蟑螂'],
      'ch06':['两只成虫保持距离缓慢相遇，无交配特写','一只雌虫与一枚完整卵鞘的自然侧面','保护性树皮缝隙内静置一枚卵鞘','另一处天然庇护所的雌虫，禁止把多种繁殖方式合在一身','两只若虫已经出现于叶脉旁，不拍破壳变形','两个若虫分开探索各自小路','一只后代的触角触碰树皮，成虫远在背景','腐木内一成虫与两若虫安静共处，明确为育幼类群意象','腐木内部纵深通道，虫体小而环境丰富'],
      'ch07':['取食腐木的野生蟑螂与木纤维','完整腐木场景，虫体外观正常，不画肠道发光球','两只白蚁在木纤维旁，直触角、无蚂蚁细腰','另一通道内单只野生蟑螂，与白蚁场景分开','森林腐木洞穴入口各自独立成景，不画亲缘树','具有自然漂亮花纹的野生蟑螂，不做荧光赛博虫','曾经湿润的腐木角落变得干燥荒凉','不同森林的新个体，落叶形状明显改变','湿润微型庇护所，水珠与阴影共存','自然木头延伸到远处木建筑门槛，文明第一次出现'],
      'ch08':['整洁木建筑内的踢脚线缝隙，小型家居蟑螂','管道附近极少水迹与食物碎屑，不做污秽厨房','远离建筑的野生蟑螂森林场景','一只蟑螂藏在运输木箱接缝，箱外遥远港口','新地点的木箱打开，安静角落的水与藏身地','整洁室内缝隙被封住，虫体藏在另一阴影','一只小型家居蟑螂停在诱饵附近，下一景无虫','另一个存活个体在不同缝隙中，不画防毒盔甲','德国小蠊停在食物前方，转身远离，小体型背部两条深纵纹','不同建筑庇护所与整洁环境，无防治步骤图','城市暖光窗外与前景一只小虫的天然裂缝'],
      'outro':['夜色落叶庇护所，安静小虫和远处倒木','不同森林小路上各自存在的小生命','水珠植物碎屑与庇护缝隙的自然场景','森林深处腐木与温暖反射光','小虫静停在缝隙入口，远方安静星夜']}
    style = ('Cinematic science-fantasy documentary landscape, calm dreamlike atmosphere, 16:9 widescreen, '
             'deep teal-blue night and controlled amber highlights, photorealistic bark, leaves, water and chitin, '
             'rich natural environmental detail, layered foreground midground background, soft volumetric moonlight, '
             'elegant asymmetrical composition. Subtle fantasy belongs to lighting and scale, never insect anatomy. ')
    anatomy = ('If a cockroach is visible: anatomically coherent cockroach, exactly six legs attached to thorax, '
               'two long segmented antennae, one intact flattened body, head partly sheltered by pronotum; '
               'natural occlusion allowed, never add limbs to expose all six. No humanoid face or expression. ')
    negative = 'No text, labels, arrows, diagram, timeline, UI, PPT, watermark, neon insect, armor, giant mutant, gore, corpse, disgusting swarm, threatening frontal closeup.'
    shots = []
    for p in paragraphs:
        if p['section']=='intro': continue
        n = int(p['id'][-2:])
        scene = scenes[p['section']][n-1]
        # Geometry-sensitive scenes deliberately use stills.
        controlled = (p['section']=='ch04' or (p['section']=='ch03' and n in [1,2,3,6,7])
                      or (p['section']=='ch06' and n in [2,3,4,5,8])
                      or (p['section']=='ch07' and n in [3,4,6])
                      or (p['section']=='ch01' and n in [6,10])
                      or (p['section']=='ch08' and n in [7,8,9,10]))
        for k in [1,2]:
            sid = f"{p['id']}-v{k:02}"
            dynamic = not controlled and (k==1 or n%2==1)
            composition = ('环境中景，虫体占画面约10%至20%，微观低机位' if k==1 else
                           '同一叙事地点的新视角，侧面宽景，强调树皮叶脉和光影，绝不裁切前一张充数')
            shots.append(dict(id=sid, paragraph_id=p['id'], utterance_ids=p['utterance_ids'],
              narration=p['text'], scene=scene, composition=composition,
              image_prompt=style+scene+'。'+composition+'。'+anatomy+negative,
              image_mode='single' if controlled or '蟑螂' in scene or '若虫' in scene or '白蚁' in scene else '2x2_tile',
              media_candidate='real_video' if dynamic else 'affine',
              motion_prompt=('One continuous calm shot. '+scene+'。Only a small natural antenna sweep or one to two slow steps if an insect is present; gentle leaf or moisture movement in the environment. Fixed camera or extremely slow drift. Preserve identity, exact limb count, body shape and environment throughout. No morphing, new object, cut, speed ramp, shake, flicker, molting transformation, aggressive chase. No generated audio.' if dynamic else '使用共享 affine，以静帧保留关键结构；不让模型生成蜕皮、数量变化或身体压扁'),
              anchor=dict(mode='actual_processed_audio', paragraph_interval_share=[(k-1)/2,k/2]),
              subclips=dict(target_seconds=[6,8], max_count=4, unique_continuations=True,
                            no_pingpong_or_identical_loop=True) if dynamic else None,
              fallback='高清静帧+共享affine；保留不合格raw并标记原因',
              status='planned'))
    # Distinct intro sources, not body-first-frame reuse.
    intro_scenes = ['月光湿润森林的低机位全景','树皮洞口深处的野生蟑螂','一颗水珠映出青蓝森林','纵深丰富的腐木通道','落叶上缓慢探索的蟑螂','苔藓与枝叶形成的微型峡谷','远方星夜下的森林树根','巨大古木基部与小小的蟑螂，上方留艺术字空间']
    for n, scene in enumerate(intro_scenes,1):
        shots.append(dict(id=f'intro-art-{n:02}', paragraph_id='intro', scene=scene,
                          image_prompt=style+scene+'。'+anatomy+negative,
                          image_mode='single' if '蟑螂' in scene else '2x2_tile',
                          media_candidate='intro_affine_layout', status='planned'))
    assert len({s['id'] for s in shots})==len(shots)
    assert all(len(scenes[sec])==sum(p['section']==sec for p in paragraphs) for sec in scenes)
    candidates = sum(s['media_candidate']=='real_video' for s in shots)
    bodyshots = len(shots)-8
    pilot = [next(s['id'] for s in shots if s.get('paragraph_id')==pid and s['media_candidate']=='real_video')
             for pid in ['ch01-p01','ch02-p02','ch02-p04','ch05-p02','ch06-p07','ch08-p01']]
    save('visual/SHOT_PLAN.json', dict(source_sha256=sha, status='planning_not_generation',
          body_shot_count=bodyshots, intro_image_count=8, real_video_candidates=candidates,
          candidate_shot_ratio=round(candidates/bodyshots,4), runtime_ratio='unknown_until_timeline',
          pilot_shots=pilot, shots=shots))
    lines = ['# 全量分镜与图片提示词\n', '每个分镜均为新素材；文稿对应、运动和回退见同目录 JSON。时间以实际音轨为准。\n']
    for s in shots:
        lines += [f"## {s['id']} — {s['media_candidate']}\n", s['image_prompt']+'\n']
        if 'motion_prompt' in s: lines += ['动态提示词：'+s['motion_prompt']+'\n']
    (ROOT/'visual/ALL_SHOT_PROMPTS.md').write_text('\n'.join(lines),encoding='utf-8')
    checks = dict(source_sha256=sha, paragraph_count=len(paragraphs), utterance_count=len(utterances),
                  runnable_utterance_count=sum(u['runnable'] for u in utterances),
                  placeholder_count=sum(not u['runnable'] for u in utterances),
                  body_shots=bodyshots, intro_images=8, video_candidates=candidates,
                  exact_text_reconstruction=True, unique_ids=True, media_executed=False)
    for path in [config['model_dir'],config['reference_wav']]:
        if not pathlib.Path(path).exists(): raise ValueError('Required path missing: '+path)
    save('PREFLIGHT.json',checks)
    print(json.dumps(checks,ensure_ascii=False))
if __name__=='__main__': main()
