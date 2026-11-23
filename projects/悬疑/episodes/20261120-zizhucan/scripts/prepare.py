from pathlib import Path
import json,re,math,hashlib
EP=Path(__file__).resolve().parents[1]
for d in ['story','storyboard','image/raw','image/final','image/plates','image/references','image/anchors','image/intro/v1','video/clips','video/final','video/srt','qa','logs']:(EP/d).mkdir(parents=True,exist_ok=True)

# Each row is one independent information beat: composition, scene, cast, fact, narration, visual.
ROWS=[
('E','mall',[], '旧商场的地下餐饮层仍在营业', '那天是老周失业后的第三个星期。我约他去吃自助小火锅，团购两个人不到一百块。商场开了很多年，楼上的店关了不少，负一楼吃饭的地方还亮着灯。', 'Wide empty older Chinese mall basement dining corridor, closed shop shutters at left, one operating hotpot doorway at right, scuffed yellow pillar and scratched steel railing, stacked delivery baskets. No people.'),
('M','entrance',['chen','zhou'], '两人正常核销团购进入餐厅', '进店时一切正常。我把团购码给前台扫了，两个人各拿一只托盘。老周还嫌我乱花钱，说自己随便吃点就行。我说钱都付了，今天总得吃回来。', 'Two young men at hotpot entrance, Chen shows his phone blank screen toward off-frame cashier, Zhou holds two trays. Foreground scratched counter edge, middle entrance, background buffet counters.'),
('E','table',[], '座位可看见饮料机却看不到出口', '我们选了靠里面的一张双人桌。右手边能看见饮料机，出口被一排冰柜挡住。桌边的黄柱子贴过胶带，留下一个颜色浅一点的方块，很好认。', 'Wide empty two-seat teal vinyl hotpot booth, yellow support pillar with rectangular tape scar on left, frosted partition right, two small steel pots on black induction plates, red-handled drink dispenser visible through counter opening, exit hidden.'),
('M','table',['chen','zhou'], '朋友把外套放在空位旁开始调料', '老周把外套搭在椅背上，熟练地拆筷子、调蘸料。他平时吃饭快，这天却坐得很慢。我们聊他的面试，他说明天还有一家，工资低一点也能先干着。', 'Young Zhou in olive overshirt sits right making sesame dipping sauce, folded dark coat on bench beside him; Chen navy jacket left opens chopsticks. Two steaming pots, tape scar pillar and frosted partition.'),
('M','table',['chen','zhou'], '主角第一次起身替朋友取牛肉', '肉盘很快就空了。我让他先吃，自己去拿牛肉。老周叫我顺便看一眼虾有没有补，我答应一声，端着空盘绕过冰柜。那时我还觉得，能让他出来吃顿饭挺好的。', 'Chen standing left holding ONE empty white oval plate, young Zhou seated right casually pointing toward buffet. Meal still ordinary, mild expressions, coat on seat, steel pots.'),
('M','counter',['chen'], '取餐只经历短暂等候', '牛肉刚好没了。我站在冰柜边等了一小会儿，才从新端出来的盘里夹了几卷。肉冻得很硬，一卷粘着一卷。我没有去别的地方，拿完就沿原路回桌。', 'Chen at frosted steel buffet meat well using tongs to lift rigid pink frozen beef curls into white oval plate, empty adjacent tray. Scratched freezer rim, chipped floor tile, stacked bowls. No worker or other diner.'),
('M','table',['chen','zhou'], '第一次回来老周已经等得不耐烦', '老周看见我，第一句话就是问我怎么去了那么久。我说才几分钟。他说自己等了四十多分钟，打了十几个电话，还出去找过我，牛肉区根本没人。', 'Chen brings frozen beef plate to booth, Zhou frowns seated and points at own phone on table. Same two young faces and same table, slightly lowered soup level.'),
('C','table',[], '两只小锅中一只已经烧干', '我想笑他太饿，低头却看见他的锅已经烧干了。锅底粘着一层黑褐色的东西，剩下的肉缩成一小块。刚才我离桌的时候，那锅汤明明才添满。', 'Close tabletop evidence, right small steel pot dry with dark brown residue and tiny shriveled cooked beef, left pot still has broth. Scratched induction plate, sauce bowl, chipped tabletop edge and water rings. No people or letters.'),
('C','table',[], '两部手机对同次呼叫留下不同记录', '他的手机里确实有一长串拨给我的电话。我的来电记录却一片空白。两部手机上的时间相同，信号也都满格。我们拨了一次，这回立刻接通了。', 'Two smartphones side by side on scratched table, both screens completely blank grey reserved surfaces without any text, numerals or icons. One olive cuff at far edge forbidden: NO HANDS OR PEOPLE. Sauce bowl and old water rings.'),
('M','table',['chen','zhou'], '两人先用正常故障解释异常', '我们试着把这件事归到信号上。地下商场，电话延迟，也许很正常。老周去加了汤，我守着桌子。他很快就回来，还问我自己走了多久。我说，不到一分钟。', 'Young Zhou returns with stainless soup kettle, Chen stays seated watching his own phone, two men exchange uncertain looks; steam resumes in right pot, wet ladle and sauce bowl.'),
('M','table',['chen','zhou'], '第二次离桌前用手机连续录像验证', '饮料喝完了，我准备去接。老周突然把手机靠在调料盒上，打开录像，正好能拍到自己和空座位。他说这次不跟我争，等我回来，直接看手机。', 'Zhou props ONE phone horizontally against sauce caddy facing his own seat, Chen stands with two empty translucent plastic cups. Clear phone orientation toward seated Zhou, not toward buffet.'),
('C','drinks',['chen'], '主角只接满两杯酸梅汤', '饮料机就在黄柱子另一边。我按住出水的把手，先接一杯，又接一杯。机器里面的酸梅汤一直在搅，我还盯着那片塑料叶子转了几圈。', 'Close young Chen navy sleeves and hands filling second of exactly two translucent tumblers with dark plum juice from red-handled dispenser, one cup already full on tray. Scratched steel drip tray and yellowed plastic, stacked cups.'),
('M','table',['chen','zhou'], '第二次回来桌上堆着许多空盘', '回来时，桌边多了一摞空盘。老周没有接饮料。他嘴唇发干，眼白里全是红丝，盯了我好一会儿，才问我，刚才到底去了哪里。', 'Chen holding two filled plum-juice cups freezes beside booth; Zhou sits right exhausted with red-rimmed eyes and dry lips, several empty plates stacked near him. No aging yet, same olive overshirt and short hair.'),
('C','table',['zhou'], '连续录像记录了六小时的等待', '手机还在拍。他按下停止，录像已经超过六个小时。我拿起来往前拖，最开始的地方，是我拿着两只空杯子离桌。连我顺手拉椅子的动作都在。', 'Close young Zhou tired face beside landscape phone on sauce caddy. Phone display contains ONLY a wordless image of the same booth and empty seat, no UI or writing. Foreground two filled cups and stacked plates.'),
('M','table',['zhou'], '老周在等待中从吃饭转为不安', '他给我看自己怎么等：先吃东西，然后看手机，后来一趟趟站起来往取餐区张望。他怕我回来找不到人，每次只敢走一小圈，马上又回到座位。', 'Young Zhou alone half-standing beside booth staring toward drink counter, empty navy-jacket mans seat, several plates before him; one hand braces table. Same fixed table perspective, no clone or reflection.'),
('M','counter',['zhou'], '寻找主角时老周摔伤脚踝', '有一次，他追着一个穿深色衣服的背影跑出去，以为是我。等他绕过冰柜，前面却没有人。他踩到地上的水，摔了一跤。现在一只脚踝肿着，鞋带已经解开。', 'Only young Zhou crouched at freezer corner after slipping, hand at swollen ankle inside loosened shoe, puddle visible foreground. No blood or second person, chipped floor, worn freezer skirting and mop bucket.'),
('E','counter',[], '熟悉的取餐区没有正常的时间变化', '这几个小时里，餐厅的灯始终一样亮，取餐台上的东西始终够吃。没人来催他，也没人撤掉我的碗筷。只有他自己越来越累，而我只是接了两杯饮料。', 'Empty buffet line in unchanged grey-blue lighting, full covered food trays, red-handled juice dispenser, stacked white bowls. Scratched freezer edge and taped yellow pillar visible. No people, shadows, text or clock.'),
('M','table',['chen','zhou'], '两人放弃吃饭共同决定立即离开', '我把饮料放下，说现在就走。老周立刻撑着桌子站起来，刚踩实那只脚，脸色就变了。我绕过去扶他，他整个人压在我肩上，后背的衣服已经湿透。', 'Chen supports young Zhou from side, Zhou winces weight off one foot; both at booth edge, two abandoned plum cups foreground, loosened shoe. No duplicate arms.'),
('M','counter',['chen','zhou'], '两人同行向出口移动', '我们一起往门口走。我一只手扶着他，另一只手沿着冰柜边缘摸过去。进来的时候，只要绕过两排柜子就能看到前台，这次我们却一直没走到。', 'Wide aisle: Chen physically supports limping Zhou, moving side by side along scratched freezer toward a bend. Foreground freezer corner occludes left; distant yellow pillar and repeating counters right. Exactly two men.'),
('E','table',[], '走过取餐区又回到同一张桌旁', '又一根黄柱子出现在前面。上面有同样的胶带印，旁边搭着老周的外套。桌上那两杯酸梅汤一口没动。我们走了一圈，回到了自己的座位。', 'Empty familiar booth from aisle, yellow pillar rectangular tape scar, olive mans dark coat draped seat, EXACTLY two dark plum cups untouched, two steel hotpots, no people.'),
('M','table',['chen','zhou'], '老周要求主角留下陪他等待', '老周坐下后，抓着我不肯放。他说不走了，让我坐着，等天亮，等商场关门，等谁来都行。他已经不在乎外面过了多久，只怕我再从他眼前消失。', 'Zhou sits right gripping Chen navy sleeve as Chen stands left, frightened tired face, same coat behind. Pots off, plate and two juice cups untouched, only two people.'),
('C','table',['chen','zhou'], '联系外界的尝试无法传出求助', '我试着报警，也给家里打电话。手机显示正在拨号，却一直没有接通。老周的手机也一样。我们把两部手机放在桌上互拨，铃声却立刻响了。', 'Close TWO young adult hands on separate smartphones on table: navy cuff left, olive cuff right; displays blank grey no UI. Distinct phone black case vs olive case, identical table water ring, no extra hand.'),
('M','table',['chen','zhou'], '主角决定沿取餐时走通的路线找出口', '坐着解决不了问题。我想起两次独自取餐，至少都能回到桌边，也许能沿那条路找到前台。我把这个想法告诉老周，让他给我一次机会。', 'Chen crouches beside seated Zhou to speak at eye level, points toward counter opening rather than touching phone. Zhou listens but keeps navy sleeve clenched. Familiar yellow pillar and cups.'),
('C','table',['chen','zhou'], '朋友以紧握手腕阻止再度离开', '他慢慢松开手，又在我起身的时候重新攥紧。我看见他不是生气，是真的怕。他已经在这张桌边等了六个小时，而我连一句有用的保证都给不了。', 'Close olive-sleeved Zhou hand firmly gripping Chen navy-cuffed wrist at scratched table edge; natural five fingers, no violence, two actors only partially visible, steel pot blurred by distance NOT shallow focus.'),
('M','table',['chen','zhou'], '主角以再拿一盘牛肉约定短暂离开', '我拿起空盘，告诉他，照刚才那样走，就去牛肉区看一眼。如果能找到前台，我就叫人过来；找不到，拿一盘肉就回来。他看着盘子，终于点了头。', 'Chen holds single empty white oval plate chest low, Zhou reluctantly releases sleeve while seated. No drink carried; pot and exactly two cups remain. Reference pose override gentle restrained gestures.'),
('C','counter',['chen'], '最后一盘牛肉仍结着霜', '这次牛肉没有缺。我夹了几卷放进盘里，肉卷表面结着一层白霜。我特意没有多拿，想着早点回去，至少别再让他对着一张空椅子。', 'Close hands of Chen using black tongs above ONE white oval plate with compact pile of rigid pink frozen beef rolls, clear white frost. Scratched freezer rim, chipped enamel bowl and stacked dishes. No blood.'),
('M','counter',['chen'], '端盘主角沿通道寻找有人值守的入口', '我端着盘子绕过冰柜，想找前台。黄柱子在身后，饮料机在左边，这些都对。可越往前，灯越少，取餐台尽头竟然出现一道明亮的玻璃门。', 'Chen carrying frosted beef white oval plate, three-quarter back walking down narrowing buffet aisle toward bright glass doorway. Red dispenser left, yellow pillar behind, steel freezer at foreground, no ghost.'),
('E','threshold',[], '餐厅通道通向重新装修的商场', '门外有人走动，我听见商场里推车轮子的声音。我推开门，终于看到了外面的扶梯。扶梯旁的护栏换了颜色，原来的广告灯箱也不见了。', 'Empty threshold toward bright ordinary Chinese shopping mall escalator and newer dark metal railing. Foreground old chipped restaurant jamb, behind modern maintained mall with scuffed floor and shopping baskets. No people or lettering.'),
('M','mall',['chen'], '主角发现身后餐厅变成药店', '我转身想回去叫老周，身后却是一家药店。玻璃门的位置没变，里面全是货架。刚刚走过的冰柜、饮料机，连同我们那张桌子，一起不见了。', 'Chen stunned holding SAME white frozen-beef plate outside drugstore entrance, inside neutral packaged pharmacy shelves without logos or writing. Glass doorway same shape, foreground scratched railing and shopping baskets.'),
('M','mall',['chen'], '主角仍端着冷肉询问失踪餐厅', '我端着肉站在门口，问这里的小火锅搬到哪儿去了。店员起初没听懂，后来告诉我，这家药店开了好几年。我以为自己上错了楼，跑到扶梯边确认，还是负一层。', 'Chen alone near mall escalator turning back toward pharmacy shelves, rigid frozen beef plate held carefully level. No employee shown, no signage, same jacket, expression disoriented.'),
('E','mall',[], '商场原有结构与店铺年代发生冲突', '我认得这座商场的楼梯，也认得墙角缺了一块的石头。它们都在，只有店换了。我沿着刚才出来的地方反复找，手里的盘子越来越重，却没有一卷肉开始化冻。', 'Close empty mall corner with familiar chipped dark stone plinth, escalator base and changed pharmacy shelving visible behind. White oval plate of frozen beef on foreground ledge, exactly one plate, no people.'),
('M','service',['chen'], '服务台凭失踪者姓名联系老周', '我去服务台求助，报了自己的名字，又说老周还在里面。工作人员听到我的名字，忽然让我先别走。她翻出一个旧文件夹，看了看我，拿起电话。', 'Chen stands holding beef plate before mall service counter, ONE closed worn unmarked document folder on counter beside landline handset; worker remains entirely off-frame. Chipped counter edge, taped cable, stacked cups.'),
('C','service',[], '旧寻人照片记录的是年轻主角', '文件夹里有一张寻人传单。纸已经发黄，折痕磨出了毛边。照片上是我，穿着现在这件外套。下面留着老周的电话号码，号码一直没换。', 'Evidence closeup yellowed paper leaflet on scratched service desk, large SINGLE wordless portrait photo of young Chen navy jacket at top, lower paper completely blank with no pseudo-writing. Distinct crossed folds and worn corners, stapled folder edge.'),
('M','service',['chen','zhou_old'], '老周以十一年后的年纪赶来', '老周赶来的时候，我差点没认出来。他两鬓有了白发，脸瘦了一圈，走路还是有点跛。他站在几步外看着我，先看脸，又看我的手，最后看向那盘肉。', 'Young Chen left holds frozen beef plate facing same Zhou now 43 on right, grey temples, fine eye lines, charcoal jacket over olive shirt, slight limp. No elder sixty appearance; recognizable face. Service desk background.'),
('C','service',['zhou_old'], '老周确认主角仍保持失踪时的样子', '他问我，是不是去拿牛肉了。我说是，拿完发现你不见了。他嘴唇动了几下，伸手碰了碰盘沿。盘子很凉，肉卷上还结着白霜。', 'Close Zhou age43 touches ceramic rim of ONE plate, frosted pink beef curls prominent below his lined face, charcoal sleeve olive inner collar, trembling restrained hand. No blood, no text, no duplicate plate.'),
('M','service',['chen','zhou_old'], '老周告知外界已过去十一年', '他告诉我，从我们进店那天算起，已经过去十一年。我低头看自己的衣服，袖口还沾着刚才调料台上的芝麻酱。对我来说，甚至还没吃完这顿饭。', 'Two men side by side, age32 Chen navy cuff has small beige sesame sauce stain and holds frozen plate, age43 Zhou charcoal jacket visibly eleven years older. Scratched counter, old folder and shopping baskets.'),
('M','table',['zhou'], '老周说明自己最终离开了空桌', '他那天又在桌边等了很久，后来实在撑不住，扶着冰柜一点点往外走。这次他找到了出口。商场里已经是两天以后，而我没有跟着出来。', 'Recounted past: ONLY young Zhou olive shirt limps alone past frozen counter toward entrance, empty chair and navy mans untouched bowl behind through gap. Fatigued, no old Zhou here, no Chen.'),
('C','service',[], '寻人记录证明等待并未困在幻觉里', '他报过警，也带人回去找过。餐厅里的桌椅还在，我不在。后来店关了，商场翻修，那里开了药店。他找不到我，只能把照片和电话留给服务台。', 'Worn unmarked folder open with SAME wordless young Chen portrait leaflet, mall floorplan drawn ONLY as plain shapes without lettering, staple rust and years of crossed folds. No official stamps or readable text, no people.'),
('M','service',['zhou_old'], '老周十一年间不断更新联络方式', '这些年，他换过工作，搬过家，唯独没换手机号。只要路过商场，就过来问一声。服务台换了人，他便把事情重新讲一遍，怕哪天我出来，连个能打的电话都没有。', 'Age43 Zhou at service desk touches old folded portrait leaflet beside own well-used phone with blank screen, posture weary but attentive, charcoal jacket olive collar; no younger version and no Chen.'),
('C','mall',['chen'], '朋友手机保留家人寻找主角的记录', '老周把手机递给我，翻出这些年保存的家人群聊。最早是我妈问我们吃完没有。后来问我在哪里，再后来，是一张张寻找我的照片。往后翻，关于我的消息越来越少。', 'Close Chen young face looking down at ONE smartphone blank neutral display, navy cuff sesame stain visible; frozen beef plate now set on service counter at side. Background pharmacy doorway. No icons or lettering.'),
('M','service',['chen','zhou_old'], '朋友帮助主角联系家人', '老周让我用他的手机给家里打电话。我按着那个熟悉的号码，手一直抖。电话接通，对面没有立刻说话。我喊了一声妈，才听见她开始叫我的名字，一声接着一声。', 'Chen holds phone to ear, face grief and disbelief, Zhou age43 stands supportively at side without touching, single frozen meat plate abandoned on desk next to folder. No third person or phone screen text.'),
('E','noodle',[], '最后一餐回到正常的街边面馆', '办完该办的事，已经很晚了。老周带我到商场楼下吃面。他替我点了以前常吃的那种，又问我要不要加蛋。我看着他，过了一会儿才说，要。', 'Wide empty worn Chinese street noodle-shop interior at night, square laminate table two steaming noodle bowls, chopstick sleeves without writing, vinegar bottle on distant counter, plastic stools, chipped tile and taped fan cable.'),
('M','noodle',['chen','zhou_old'], '十一年改变朋友而没有改变主角', '他拆开筷子递给我，动作跟吃小火锅时一样。我想问他这些年过得怎么样，话到了嘴边，又不知道从哪一年问起。他已经吃了很多顿饭，我还停在那一顿。', 'Young Chen seated left and middle-aged Zhou right at noodle table, Zhou offers unwrapped wooden chopsticks, two steaming noodle bowls. Same navy vs charcoal-over-olive clothes, old shop, no frozen meat plate here.'),
('C','noodle',['chen','zhou_old'], '拿醋的日常动作再次触发抓腕', '桌上没有醋。我撑着桌沿，刚想站起来，老周的手就按住了我的手腕。我看了看不远处的醋瓶，重新坐好。他没有松手。', 'Close olive and charcoal cuff hand gently but urgently pressing navy-cuffed wrist onto chipped noodle table; two noodle bowls steam, black vinegar bottle visible far counter. No violence, clean deliberate cel contours, only two men.'),
]

shots=[];frame=0
for i,(kind,scene,cast,fact,cue,visual) in enumerate(ROWS,1):
 n=len(re.sub(r'[^\u4e00-\u9fffA-Za-z0-9]','',cue))
 sentences=max(1,len(re.findall('[。！？]',cue)))
 frames=math.ceil((n/3.6+sentences*.24)*24)
 shots.append(dict(id=f'S{i:02}',cue=cue,shot_type=kind,scene_id=scene,fact=fact,visual=visual,
  character_ids=cast,has_character=bool(cast),line='悬疑',step='single',character_closeup=kind=='C' and bool(cast),hands_visible=kind=='C' and bool(cast),evidence_id=f'EV-{i:02}' if kind=='C' else '',subject_class='character' if cast else 'environment',push_ratio=.096 if kind=='C' else 0,needs_2048=kind=='C',
  start_frame=frame,frames=frames,start=frame/24,end=(frame+frames)/24,duration=frames/24,
  motion='static' if i in [8,9,14,17,20,22,28,31,33,35,38,40,45] else 'affine',
  production_mode='single',single_reason='跨镜同场母题定装及证据关系独立整幅；人物正侧脸与关键动作可读性优先',foley_requirement='none'))
 frame+=frames
plan=dict(title='你先吃，我马上回来',fps=24,frames=frame,duration=frame/24,shots=shots,estimated=True)
(EP/'storyboard/SHOT_PLAN.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2))
script='# 你先吃，我马上回来 · 正文锁定稿\n\n第一人称虚构叙述者：陈默，32 岁。只讲亲历及老周明确转述。引入不进入正文。\n\n'
for s in shots:
 script+=f"{s['id']} {s['cue']}\nshot_type：{s['shot_type']}\nscene_id：{s['scene_id']}\nfact：{s['fact']}\nhas_character：{str(s['has_character']).lower()}\nvisual：{s['visual']}\n\n"
(EP/'story/script.md').write_text(script)
(EP/'story/intro.md').write_text('# 已确认引入\n\n我去拿了盘牛肉，回来时，朋友老了十一岁。\n\n他等了我十一年。而我端着的肉，还没化冻。\n\n画面1：年轻陈默端冷冻牛肉面对43岁的老周，重逢发生在变成药店的餐厅外服务台。\n画面2：带霜牛肉与老周明显年长的手同框，盘沿被手指触及。\n\n单独两图，不剪入正文、不制作字幕。正文起始句：那天是老周失业后的第三个星期。\n')
(EP/'story/outline.md').write_text('''# 故事主线与悬念预算

1. 两名32岁朋友正常团购吃自助小火锅；座位、黄柱胶带印、饮料机建立地图。
2. 陈默取牛肉几分钟，老周等四十多分钟：干锅与不同电话记录互证。
3. 老周主动连续录像；陈默接两杯饮料回来，他已等六小时，寻找过程中扭伤脚踝。
4. 两人尝试同行离开，却回到原桌；拨外线无法接通，桌内互拨正常。
5. 不愿继续坐等，陈默沿曾走通的取餐路线寻前台；老周怕再等，最终同意。陈默端少量冻肉承诺短暂离开。
6. 陈默找到门，走进已翻修的商场，身后餐厅已改药店；牛肉未解冻证明自身时间短。
7. 服务台旧寻人传单改写“局部等待”：陈默是十一年前的失踪者。43岁的老周赶来，确认冷盘，讲清自己两天后离店并在外界等待十一年的行动线。
8. 陈默通过老周保存的记录得知家人寻找经过，并用对方手机联系家人，正视失去的年月；面馆取醋时老周再次抓腕，回收桌边阻止离开的动作。

| 悬念 | 回收 |
|---|---|
| 主：几分钟取餐为什么让同伴等那么久？ | 电话、连续录像、寻人传单递进证明取餐通道把陈默跳到更晚时刻；外界时间真实前进。并非朋友说谎或手机故障。 |
| 次：两人能否离开、老周是否被留在店里？ | 老周两天后独自走出；陈默十一年后走出并重逢，二人均离开。 |
| 仅保留未知 | 异常餐厅来源；陈默如何重新进入生活。 |

世界规则只要求理解两项：陈默独自走取餐通道会越过外界时间；等待者与世界正常经历这段时间。路线错位与通讯受限是同一隔绝的表现，不增加替身、献祭、旧物或可操纵的命名机制。

证据：烧干的小锅与对不上来电记录（第一次排除记时失误）；连续录像（实证真实等待）；旧寻人传单和不化冻牛肉（把时间变化延伸到外界并兑现引入）。证据文书只展示无字照片、折痕和道具关系，不在画面添加文字/UI。

原作保留：普通自助用餐成为恐怖处境的抽象母题。
必须重写：人物、事件、异常机制、完整证据与结局。
本土化新增：团购核销、小火锅冻肉、蘸料台、商场服务台、街边面馆。
预期反转：朋友实际在外界等待十一年；冻肉与年轻失踪照重释前两次的迟归。

采用用户最新“可以，现在开始做吧，直到出成品”授权，自主完成本文、图像、视频、字幕及技术验收，不再次请求逐阶段确认。关键动态以可控图层/起止状态表现为初始方案，不承诺人物连续表演或I2V。
''')
chars=sum(len(re.sub(r'[^\u4e00-\u9fffA-Za-z0-9]','',s['cue'])) for s in shots)
(EP/'story/budget.json').write_text(json.dumps(dict(target_minutes=13,target_chars=2808,actual_visible_chars=chars,actual_timeline_seconds=frame/24,cps=3.6,shots=len(shots),timing='估算时间轴，未对真实人声校准'),ensure_ascii=False,indent=2))
(EP/'INPUT_zizhucan.md').write_text(f'''# 单集输入

- 标题：《你先吃，我马上回来》
- 母题：男子取餐跨过十一年，与变老的朋友重逢，失去的时间无法取回。
- 主线/悬念/物证/结尾：见 story/outline.md；八节点，完整回收，结尾抓腕。
- 视角：第一人称虚构陈默，只讲亲历与老周转述。
- 目标：13分钟，总预算2808字，实际{chars}字；时间轴{frame/24:.3f}秒，{len(shots)}镜。
- 来源：初始参考 r/nosleep · u/Asteroth6 · https://www.reddit.com/r/nosleep/comments/1x8ghok/how_to_get_the_most_out_of_the_allyoucaneat_buffet/ 。仅保留抽象自助恐怖母题，全部具体情节重新编写；保守登记 authorization-pending，授权由用户闭环，不阻塞本次执行。
- 必须覆盖：已确认两句引入原文；冻牛肉和十一年重逢必须兑现。
- 必须避免：旧物换饭、替身分支、血腥、片内文字和音轨。
- 交付：两张引入图独立交付、正文MP4、同基名SRT。
''')
(EP/'PROJECT_STATE.md').write_text('''# 你先吃，我马上回来 · 当前制作状态

- 2026-11-20：用户授权“可以，现在开始做吧，直到出成品”。当前完成输入单、故事主线、悬念预算、总字数预算及完整正文；下一步门禁、角色锚点与分镜制作。
- 本集局部执行：用户要求直到成品，自主完成阶段验收，不等待重复确认。画面主计划为调查漫画静帧、浮点推拉/平移和证据起止状态，未将I2V列为计划，不作失败后静默回退。
- 引入：保持用户确认两句，单独两图，不进正文。最后一次取餐端冻牛肉沿通道找出口，出来后重逢年长朋友，使引入有正文支撑。
- 来源状态：authorization-pending，用户接管；不冒称取得书面许可。
- 成品规格：1920×1080 / 24fps，无音轨、无字幕流、无烧录字幕；独立正文SRT。
''')
(EP/'logs/authorization.json').write_text(json.dumps({'at':'2026-11-20 Asia/Shanghai','user_instruction':'可以，现在开始做吧，直到出成品','scope':'完成当前单集正文、分镜、图像、引入独立两图、正文视频与SRT，自动执行阶段验收。','not_authorized':'更改长期规则、发布或发送外部消息','source_license':'authorization-pending'},ensure_ascii=False,indent=2))
print(json.dumps({'shots':len(shots),'visible_chars':chars,'duration':frame/24},ensure_ascii=False))
