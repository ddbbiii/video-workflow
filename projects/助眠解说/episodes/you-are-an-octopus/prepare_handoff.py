"""Build text-only production plans; never launches media or changes runtime state."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
WORK = ROOT.parents[3]
STYLE = ('Cinematic science-fantasy underwater documentary, calm dreamlike mood, '
         '16:9 widescreen, deep teal-blue with controlled amber caustics, '
         'photorealistic skin, rock, sand and water, intricate material detail, '
         'layered foreground midground background, soft volumetric light, '
         'elegant asymmetrical composition. Fantasy is confined to atmosphere and lighting. ')
NEG = ('No text, letters, numbers, captions, labels, arrows, diagrams, UI, PPT, '
       'watermark, city, robot, jewelry, armor, human face, gore, mutated anatomy, '
       'extra arms, tentacle tangle, oversaturated neon, threatening closeup. ')
ANATOMY = ('One anatomically coherent octopus unless explicitly specified otherwise: '
           'one mantle, one head, eight arms belonging to this animal, natural occlusion '
           'allowed; never force every arm into view or add arms. Suckers on ventral arm '
           'surfaces, no squid feeding tentacles, no human fingers. ')

# Each marker is the first literal paragraph of a distinct narrative beat.
# Scene and permitted internal motion are authored here, not invented during assembly.
BEATS = {
 'bridge': [('不过，今天的你', '空旷古海与前景螺旋贝壳，远景只有柔和水光，不画现代章鱼变身', '细小悬浮颗粒缓慢漂移', False)],
 'ch01': [
 ('你睁开眼', '晚寒武世浅海沉积物宽景，低矮微生物底质与零星小型无脊椎轮廓，没有现代珊瑚礁', '细小水中颗粒漂移', True),
 ('你现在带着一只壳', '一只早期带壳头足类的保守复原，短直锥形分室外壳，壳口软体少量露出，禁止现代鹦鹉螺冒充祖先', '水中颗粒轻移，动物形态保持不变', True),
 ('你不能像后来', '带壳动物停在无法容纳外壳的窄石缝外，侧面中景明确壳宽与缝宽关系', '背景水光缓慢变化，动物静止', True),
 ('不过，壳并不只是', '完整带壳动物在水中悬浮的场景，不剖切，不画气室示意，不加漂浮气泡箭头', '背景颗粒轻移，动物不变形', True),
 ('这件事很重要', '古海开阔水层里的带壳头足类，低机位宽景、下方沉积物与稀疏猎物轮廓', '开阔水层悬浮颗粒漂移', True),
 ('但开阔的海水', '带壳动物近景与远方模糊掠过的较大古海生物轮廓，安全距离，不指定无依据物种', '背景水光轻移，不追逐不攻击', True),
 ('它不是错误', '一只完整带壳头足类安静悬浮，琥珀边光照亮壳面细纹，古海背景', '细颗粒缓慢漂移', True),
 ('后来，带壳头足类', '不同天然贝壳各自落在古海石面，形态多样而非演化队列，精致壳面材质', '无模型动态，保留形态', False),
 ('今天还能看见', '现代鹦鹉螺单独在深蓝海水里，天然卷壳与壳口众多细触手，禁止八腕章鱼解剖', '缓慢水中颗粒，不新增腕足', True),
 ('现在，海水仍然', '回到古海短直壳动物，沙底微小猎物在壳口前，侧面安静构图', '背景悬浮颗粒轻移，不捕杀', True)],
 'ch02': [
 ('海水变深了', '深蓝古海纵深宽景，柔和下射光和黑暗海床，没有现代人工建筑', '悬浮颗粒缓慢下沉', True),
 ('头足类里', '独立鱿鱼侧面全身照，纺锤形外套膜与鳍自然，八腕加一对长触腕，不当作章鱼祖先', '背景水光轻移，解剖形态静止', True),
 ('壳进入身体', '独立乌贼全身中景，宽扁外套膜与裙边鳍，真实皮肤，禁止透明剖面或骨架标注', '背景悬浮颗粒漂移', True),
 ('你站在一条', '浅海章鱼与一只小甲壳类保持距离，岩礁错落，未发生捕猎', '一条已有腕足末端微微探索，不改变腕数', True),
 ('对主动捕食', '章鱼在两块礁石之间选择通道，侧后方宽景，前方有足够空间', '已有腕足末端小幅移动，身体不穿石', True),
 ('但我们不能', '安静空海床与一枚天然贝壳，表现环境差异而非主动丢壳过程', '柔和水光移动', True),
 ('与此同时', '完整章鱼侧面，漏斗位置自然可见但不做解剖，不添加水流箭头', '水中颗粒轻移，不喷射大变形', True),
 ('平时，你可以', '章鱼靠近洞口，岩石形成向外开阔的退路，安全距离无捕食者扑咬', '一条腕足末端轻探，不急速逃跑', True),
 ('没有厚重外壳', '章鱼停在岩缝口，暗处与远方暖光形成安全和开阔空间对照', '细颗粒缓慢漂移', True),
 ('你伸进去一条', '岩缝入口中景，章鱼一条已有腕足接触石面，身体仍完整处于缝外', '已接触的腕端微动，不让整个动物穿缝', True)],
 'ch03': [
 ('你进入岩缝', '已在宽阔岩缝内的章鱼，入口透入金色水光，躯体不挤压变形', '洞口水光轻移', True),
 ('有些食物', '岩礁小洞旁一只甲壳类与远处章鱼，不发生捕杀，空间关系清楚', '细颗粒漂移', True),
 ('在现代头足类', '独立章鱼全身宽景，腕足自然分布在海床，八腕结构保持，不做对比图', '背景水光轻移', True),
 ('八条，并不意味着', '独立鱿鱼自然全身照，八腕与两条捕猎触腕属于同一个体，不做腕足脱落演化', '无模型动态，保留精密结构', False),
 ('在今天黎巴嫩', '无标签的浅色石灰岩上软体章鱼化石印痕，研究式保守表现，不用鲜活章鱼埋在石头里', '无模型动态，保留化石', False),
 ('这不是章鱼', '石灰岩断面近景与深色环境，真实沉积层纹理，不画年代尺', '无模型动态，保留证据性质', False),
 ('现在，把目光', '现代章鱼从洞口伸出一条腕足，吸盘贴石，侧面中景', '已有腕足末端细小探索', True),
 ('腕足中的肌肉', '单条章鱼腕足连接完整主体，自然弯曲贴在岩面，湿润皮肤和吸盘细节', '腕端小幅自然弯曲，不拉成橡胶', True),
 ('但柔软也不是', '章鱼停在极窄裂口之前，完整头部与身体，不做无限挤压', '背景水光轻移', True),
 ('这时，你还没有', '章鱼安全停在较宽洞口，低机位宽景，周围岩礁层次丰富', '颗粒缓慢漂移', True)],
 'ch04': [
 ('洞口外', '一只螃蟹在岩石后，章鱼在前景，明确相互遮挡与距离', '环境细颗粒漂移，不让螃蟹消失', True),
 ('你把一条腕足', '章鱼一条已有腕足触碰粗糙岩面，吸盘湿润细纹可见，主体连接清楚', '腕端微小接触调整', True),
 ('章鱼的吸盘', '真实吸盘宏观特写，连接于自然腕足，石面附着微小生物膜，不画舌头神经光球', '无模型动态，保留吸盘细节', False),
 ('眼睛适合', '章鱼侧脸中景与前景腕足，眼睛看向远处而腕足进入石后', '悬浮颗粒轻移，眼睛不变形', True),
 ('你的腕足中', '完整章鱼在礁石间自然探索，腕足连接同一主体，不透视神经或画八个大脑', '一条腕端轻探，其余稳定', True),
 ('但这也不是', '章鱼以不同腕足固定在两块石面，整体协调构图', '背景水光轻移', True),
 ('螃蟹往后退', '螃蟹钳与章鱼腕端保持安全距离，侧面未接触画面，不做搏斗', '水中颗粒漂移，不重复后退动作', True),
 ('最终，猎物', '章鱼靠近已静置的甲壳类，避免口部猎杀特写，细节清楚无血腥', '无模型动态，避免猎物融化', False),
 ('你的身体', '章鱼安静停在海床，皮肤细节与礁石光影相映，完整身体', '小幅已有腕端探索', True)],
 'ch05': [
 ('一片阴影', '章鱼伏在石面，远处大鱼模糊剪影，上方阴影但没有攻击', '只有背景细颗粒移动', True),
 ('这一次', '章鱼已经贴近石面，纹理和颜色接近石头，完整动物轮廓仍可辨认', '环境水光轻移，不消失', True),
 ('章鱼的伪装', '章鱼皮肤自然色素斑与细小乳突宏观近景，不用网格像素图或细胞示意', '无模型动态，保留皮肤', False),
 ('颜色、纹理', '章鱼与粗糙礁石的侧面中景，颜色纹理姿态共同融入环境', '背景水光移动，不重塑皮肤', True),
 ('这不是你', '伪装章鱼仍清晰连接自身腕足，海底环境高级精致而非石头变动物', '轻微颗粒漂移', True),
 ('许多时候', '空旷水层与前景隐蔽章鱼，没有反复游过的敌人', '柔和水光移动', True),
 ('但伪装', '开阔沙地上的章鱼，周边缺少遮挡，无敌人嘴部特写', '腕端轻微试探', True),
 ('水从漏斗', '已扩散的少量墨云在远处海水中，章鱼在安全洞口，禁止喷墨爆炸或捕食', '既有墨云单向缓慢扩散，不循环', True),
 ('我们不知道', '章鱼安静藏在礁石阴影，现代场景，不配虚构古年代', '背景颗粒缓慢漂移', True)],
 'ch06': [
 ('这一片海底', '宽阔热带火山沙地，少量海底孔洞，暂无章鱼，丰富沙粒纹理', '水中细颗粒轻移', True),
 ('其中，有一种', '单只拟态章鱼在沙地，细长八腕、自然黑白条纹，禁止小飞象鳍', '一条腕足末端小幅移动', True),
 ('它能够', '拟态章鱼保持展平的既定自然姿态在沙地，禁止变成鱼蛇或混种', '无模型动态，保持拟态结构', False),
 ('换一种轮廓', '拟态章鱼低机位侧面与宽阔沙地，远处鱼小且模糊', '背景颗粒轻移', True),
 ('再往更深', '深海广阔水层，冷蓝暗光、海雪、无阳光柱到达深渊', '海雪颗粒缓慢下沉', True),
 ('你也许见过', '单只小飞象章鱼，圆润外套膜两侧一对天然鳍、腕间蹼、八腕，禁止条纹拟态章鱼', '一对已有小鳍轻轻摆动，不增加鳍', True),
 ('没有强烈阳光', '深海小飞象章鱼远景悬浮，海雪与黑暗纵深，不画人工灯和城市', '海雪下沉，已有鳍微动', True),
 ('有些亲族', '单只幼小浅海章鱼在蓝色水层中漂浮，细小透明轮廓，不复制群体', '周围颗粒轻移', True),
 ('为了继续', '回到浅海礁石章鱼，岩缝、沙地与金色反光，明确与深海不同场景', '一条已有腕端探索', True)],
 'ch07': [
 ('你又来到', '章鱼停在倾斜岩石侧面，螃蟹隐藏于深处，不重演失败搏斗', '背景颗粒轻移', True),
 ('这一次', '章鱼从岩石另一侧接近，构图明确可行路线，未接触猎物', '一条已有腕端轻探', True),
 ('对你来说', '章鱼腕端触石，近景材质细腻，不放教室桌椅', '微小腕端探索', True),
 ('在实验环境', '简洁真实海水研究缸内一只章鱼与一个透明食品容器，无标志文字无实验图表', '背景水流轻移，容器静止', True),
 ('人们尤其喜欢', '章鱼腕足贴着关闭的透明容器，器皿边缘结构可信，不生成打开过程', '无模型动态，保持器皿结构', False),
 ('不过，一段精彩', '研究缸章鱼独立新角度，容器在远处而非主体，安静停留', '已有腕端小幅活动', True),
 ('一只螃蟹', '章鱼在倾斜石另一侧，一只螃蟹处于可接近的狭小空隙，不做抓捕', '环境悬浮颗粒轻移', True),
 ('你的聪明', '章鱼探索有三层岩礁的开阔海床，前景粗石、主体中景、远景水光', '一条已有腕端探查', True),
 ('可是，人类', '独处章鱼望向空旷海底，不画章鱼城市、人类工程师或文明阶梯', '柔和悬浮颗粒移动', True)],
 'ch08': [
 ('你认识这块', '章鱼在熟悉岩缝前安静停留，细腻石面与吸盘，单个主体', '已有腕端微动', True),
 ('你的记忆', '另一处独立场景中的幼小章鱼，岩石尺度更大，不画记忆传输特效', '悬浮颗粒漂移', True),
 ('经验想留下', '两只同种章鱼远距离处于不同洞穴入口，各自完整，无亲子教学动作', '背景颗粒漂移，不交互', True),
 ('但你的生活', '单只章鱼在独立庇护所，周围无人，景观细节丰富', '一条已有腕端微动', True),
 ('这不是说', '两只章鱼隔着足够距离位于不同石面，侧面宽景，不做拥抱或人类对话', '仅水中颗粒缓慢漂移', True),
 ('在许多章鱼', '雌性章鱼与一小簇附着洞顶的卵，完整软体，卵不发光不变眼球', '环境细颗粒轻移，卵簇不动', True),
 ('还有时间', '浅海独处成年章鱼中景，皮肤自然纹理，没有计时器钟表', '已有腕端轻微移动', True),
 ('于是，我们看见', '章鱼熟练伏在倾斜石侧面，独处景观而非成败排行榜', '背景水光移动', True),
 ('后来，洞穴里', '雌性章鱼守在洞顶卵簇下方，宽景明确洞穴位置，禁止孵化和死亡变形', '轻柔水中颗粒，卵保持附着', True)],
 'ch09': [
 ('洞口的光', '雌性浅海章鱼守卵洞穴，暖光洞口与冷蓝内部，少量真实卵串附着顶面', '环境细颗粒轻移', True),
 ('从这里开始', '同一类雌性章鱼独立侧面近景，守卵姿态，禁画雄性同时产卵', '细小腕端清理动作，不接触卵引发变形', True),
 ('你调整身体', '雌性章鱼靠近卵串，腕端在附近而非缠断卵，侧面中景', '细颗粒表示缓慢水流，卵静止', True),
 ('在许多种类', '守卵雌性安静停在洞内，正常皮肤，避免饥饿血腥和尸体', '环境水光轻移', True),
 ('研究者也在', '章鱼正常眼部和头部侧面近景，真实皮肤，禁止虚构可见视腺或死亡开关', '无模型动态，保留头部细节', False),
 ('守护需要多久', '冷暗深海岩壁上单只守卵章鱼，稀疏海雪，非浅海日光洞穴', '海雪缓慢下沉，卵不晃动', True),
 ('你面前的这些', '洞顶自然半透明卵串细节，卵囊中形态朦胧，不画人类胎儿', '无模型动态，不生成破卵', False),
 ('终于，有一枚', '已经孵化的一只幼小章鱼在卵簇外，完整八腕，避免卵转成动物的过程', '微小水中颗粒漂移', True),
 ('我们在故事里', '独立幼小章鱼在小石面探索，远方模糊洞穴，无母亲传递地图', '已有腕端极小幅触碰石面', True)],
 'ch10': [
 ('你又睁开眼', '新一代章鱼在另一片岩礁醒来式停留，布局与开篇不同，无人类眼睑动作', '细颗粒缓慢移动', True),
 ('但继续', '完整章鱼自然体型静停海床，不画巨型怪物或进化阶梯', '已有腕端微动', True),
 ('从早期带壳', '现代海床上的一枚自然空贝壳与远处章鱼，非直接祖先家谱', '背景水光轻移', True),
 ('失去外壳', '柔软章鱼停在合适宽度岩缝，身体不压扁，不做变身', '背景悬浮颗粒轻移', True),
 ('这些办法', '章鱼在丰富岩礁层次中安静生活，真实皮肤与石面反光', '已有腕端轻探', True),
 ('今天的海洋', '礁石环境与远方水层宽景，自然海藻稀疏，不画灾难或末日建筑', '海藻末梢轻柔摆动', True),
 ('现在，我们暂时', '章鱼沿石面停留，吸盘接触石头，低机位舒缓构图', '一条已有腕端小幅探索', True),
 ('上方有一道', '章鱼已伏低融入礁石，远方仅静态模糊阴影，避免重复捕食事件', '环境颗粒漂移', True),
 ('你没有骨头', '完整章鱼安静侧面，八腕自然遮挡，有精致材质与温柔金色边光', '已有腕端小幅移动', True),
 ('水流轻轻经过', '章鱼已经安顿在岩缝内部，远方柔和蓝光，宁静结尾不追逐', '背景水光慢移，动物静止', True)]}

def save(rel, data):
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--body-seconds', type=float)
    parser.add_argument('--intro-seconds', type=float, default=25)
    args = parser.parse_args()
    source = ROOT / 'story/NARRATION_MASTER.md'
    original = source.read_text(encoding='utf-8')
    sha = hashlib.sha256(source.read_bytes()).hexdigest()
    sections = re.findall(r'^## ([^\n]+)\n(.*?)(?=^## |\Z)', original, re.M | re.S)
    assert len(sections) == 12
    paragraphs, utterances, shots = [], [], []
    config = dict(out_dir=str(ROOT / 'audio/vo-raw/seed7'),
                  model_dir=str(WORK / 'shared/runtime/engines/tts/voxcpm/pretrained_models/VoxCPM2'),
                  mode='ultimate', seed=7, cfg_value=2.0, inference_timesteps=10,
                  desc='', desc_in_text=False,
                  reference_wav=str(WORK / 'shared/runtime/engines/tts/refs/b2-warm-male_ref.wav'),
                  prompt_wav=str(WORK / 'shared/runtime/engines/tts/refs/b2-warm-male_ref.wav'),
                  prompt_text='发电机就在外核。液态铁被热量推着翻滚，切过磁场，生出电流，电流又生出磁场。地面上的罗盘，感受到的就是这股磁场。它藏在很深的地下，安安静静，日夜不息。')
    for ix, (title, body) in enumerate(sections):
        sec = 'intro' if ix == 0 else 'bridge' if ix == 1 else f'ch{ix-1:02}'
        paras = [p.replace('\n', '') for p in re.split(r'\n\s*\n', body.strip()) if p.strip()]
        local = []
        for n, p in enumerate(paras, 1):
            pid = f'{sec}-p{n:03}'
            chunks, current = [], ''
            for sentence in re.findall(r'[^。！？]+[。！？]?', p):
                if current and len(current + sentence) > 110:
                    chunks.append(current)
                    current = ''
                current += sentence
            if current:
                chunks.append(current)
            assert ''.join(chunks) == p
            ids = []
            for k, chunk in enumerate(chunks, 1):
                uid = f'{pid}-u{k:02}'
                ids.append(uid)
                utterances.append(dict(id=uid, paragraph_id=pid, section=sec, text=chunk,
                                       runnable='【' not in chunk))
            row = dict(id=pid, section=sec, text=p, utterance_ids=ids)
            local.append(row)
            paragraphs.append(row)
        ready = [dict(id=u['id'], text=u['text']) for u in utterances if u['section']==sec and u['runnable']]
        save(f'audio/jobs/{sec}.json', dict(config, shots=ready))
        save(f'audio/gate/{sec}-shotlist.json', dict(title='你是一只章鱼', profile='b-sleep', language='zh', shots=ready))
        if sec == 'intro':
            continue
        specs = BEATS[sec]
        boundaries = []
        for marker, *_ in specs:
            matches = [n for n, p in enumerate(local) if p['text'].startswith(marker)]
            assert len(matches) == 1, (sec, marker, matches)
            boundaries.append(matches[0])
        assert boundaries == sorted(set(boundaries)) and boundaries[0] == 0
        for b, (marker, scene, motion, dynamic) in enumerate(specs):
            selected = local[boundaries[b]:boundaries[b+1] if b+1<len(boundaries) else len(local)]
            bid = f'{sec}-b{b+1:02}'
            for view in (1, 2):
                sid = f'{bid}-s{view:02}'
                real = dynamic and view == 1 and sec != 'bridge'
                camera = ('侧面环境中景，主体在右侧三分之一，前景低矮岩缘、中景主体、远景蓝色海水，主体占宽约25%，保留左侧空间。' if view == 1 else
                          '独立新构图的低机位宽景，主体在左侧三分之一，前景细砂或石纹、中景主体、远景水光，主体占宽约15%，不是上一图裁切或放大。')
                if '近景' in scene or '特写' in scene:
                    camera = ('独立细节近景，关键材质占画面约50%，仍保留自然连接与环境，侧面柔光。' if view == 1 else
                              '独立斜侧中景，将同一知识点放回真实栖息环境，主体占画面约30%，不裁切前图。')
                special = any(w in scene for w in ['小飞象', '拟态', '化石', '鹦鹉螺', '鱿鱼', '乌贼', '暂无章鱼', '不画现代章鱼'])
                anatomy = ANATOMY if '章鱼' in scene and not special else 'Preserve only the explicitly described subject and species anatomy; do not add an octopus or substitute another species. '
                strategy = 'V3' if real else 'P1'
                # Only particles/sway on fixed backgrounds may repeat; dispersal and exploration are one-way.
                shots.append(dict(id=sid, beat_id=bid, section=sec,
                    paragraph_ids=[p['id'] for p in selected], narration=''.join(p['text'] for p in selected),
                    scene=scene, composition=camera, image_prompt=STYLE+scene+'。'+camera+anatomy+NEG,
                    image_mode='single' if any(w in scene for w in ['特写','化石','吸盘','容器','拟态','小飞象','鹦鹉螺','鱿鱼','卵']) else '2x2_tile',
                    shot_class='image_to_video' if real else 'image_camera_motion', strategy=strategy,
                    motion_prompt=('One continuous original-speed calm shot. '+scene+'。'+motion+'。 Preserve identity, anatomy, arm count, suckers, eyes, attached eggs and rock geometry. No cuts, shake, flicker, blur pulses, morphing, hatching, predation, sudden objects, reverse, speed ramps or generated audio.') if real else None,
                    loop_allowed=False, tail_extension_seconds=2 if real else 0,
                    image_motion=dict(direction='push_in' if view==1 else 'pan_right', reference_scale=[1.02,1.10], endpoint_hold_seconds=0),
                    timing=dict(mode='actual_aligned_audio_beat', order=view,
                        allocation='first_dynamic_8_to_12s_plus_2s_tail_then_second_image_remainder' if dynamic and sec!='bridge' else 'two_images_equal_audio_share',
                        short_beat='if_beat_under_12s_use_two_P1_images_equal_share',
                        native_seconds_reference=[8,12], max_tail_seconds=3.5,
                        overflow='split_remaining_P1_into_distinct_extra_view_from_locked_scene_prompt_every_24s'),
                    status='planned'))
    intro_scenes = [
        '浅海礁石宽景，金色月光穿水，左前景安静章鱼',
        '章鱼自然眼部侧面与粗糙岩面，极精致皮肤',
        '深海小飞象章鱼独立全身，天然两鳍与蹼，深蓝海雪',
        '古海短直壳头足类，壳面细纹与琥珀轮廓光',
        '章鱼已伪装伏在礁石上，自然纹理，未变身',
        '岩缝中的章鱼与洞外蓝色水光，细腻吸盘',
        '拟态章鱼在火山沙地自然静置，细长八腕条纹',
        '完整现代浅海章鱼在绚丽大尺度礁石景观，主体居中下方，上方留艺术字空间，不复用正文第一镜']
    for n, scene in enumerate(intro_scenes,1):
        shots.append(dict(id=f'intro-art-{n:02}', section='intro', scene=scene,
                          image_prompt=STYLE+scene+'。'+NEG+'Preserve explicitly named species anatomy; no extra arms.',
                          image_mode='single', shot_class='intro_affine_layout', status='planned'))
    assert len({s['id'] for s in shots}) == len(shots)
    covered = [pid for s in shots if s.get('id', '').endswith('-s01') for pid in s['paragraph_ids']]
    expected = [p['id'] for p in paragraphs if p['section'] != 'intro']
    assert covered == expected, 'Narration coverage has gaps, repeats or reordered paragraphs'
    assert all(s['loop_allowed'] is False for s in shots if 'loop_allowed' in s)
    assert all(Path(config[k]).exists() for k in ['model_dir', 'reference_wav', 'prompt_wav'])
    save('audio/utterances.json', dict(source_sha256=sha, paragraphs=paragraphs, utterances=utterances))
    save('visual/SHOT_PLAN.json', dict(source_sha256=sha, shots=shots,
         pilot_shots=['ch01-b02-s01','ch04-b02-s01','ch05-b08-s01','ch06-b06-s01','ch08-b09-s01','ch10-b10-s01']))
    prompt_lines = ['# 全量镜头提示词\n', '机器真源为SHOT_PLAN.json；以下镜头全部新生成，不复用旧集资产。\n']
    for s in shots:
        prompt_lines += [f"## {s['id']}\n", f"对应口播：{s.get('narration','片头独立素材')}\n",
                        f"组合：{s.get('strategy','片头布局')}；{s['image_mode']}\n",
                        f"图片：{s['image_prompt']}\n", f"动态：{s.get('motion_prompt') or '不生成模型动态'}\n"]
    (ROOT/'visual/ALL_SHOT_PROMPTS.md').write_text('\n'.join(prompt_lines),encoding='utf-8')
    if args.body_seconds is not None:
        if not math.isfinite(args.body_seconds) or args.body_seconds<=0 or not math.isfinite(args.intro_seconds) or args.intro_seconds<=0:
            raise ValueError('Provide positive measured audio durations')
        minute = math.floor((args.body_seconds+args.intro_seconds)/60+.5)
        u = next(u for u in utterances if not u['runnable'])
        resolved = u['text'].replace('【正文实测分钟数】',str(minute))
        save('audio/jobs/intro-minute-resolved.json',dict(config,shots=[dict(id=u['id'],text=resolved)]))
        save('audio/intro-minute-resolution.json',dict(minute=minute,body_seconds=args.body_seconds,
             intro_seconds=args.intro_seconds,status='recheck_with_actual_intro',source_sha256=sha))
        (ROOT/'story/NARRATION_RESOLVED.md').write_text(original.replace('【正文实测分钟数】',str(minute)),encoding='utf-8')
    report = dict(status='text_plan_validated_not_media_generated',source_sha256=sha,
                  paragraphs=len(paragraphs),utterances=len(utterances),
                  unresolved_utterances=sum(not u['runnable'] for u in utterances),
                  body_shots=sum(s['section']!='intro' for s in shots),intro_images=8,
                  dynamic_candidates=sum(s['shot_class']=='image_to_video' for s in shots),
                  chinese_characters=sum(len(re.findall(r'[\u4e00-\u9fff]',u['text'])) for u in utterances))
    assert report['unresolved_utterances']==1
    save('PREFLIGHT.json',report)
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__ == '__main__':
    main()
