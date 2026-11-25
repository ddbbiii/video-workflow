"""Map original paragraphs to explicit visual beats without rewriting narration."""
from pathlib import Path
import json, re, math, hashlib

EP = Path(__file__).resolve().parents[1]

# Section / final paragraph index / scale / place / cast / visible fact / visual action.
DATA = '''
0|1|E|village|none|暑期山村是案件发生地|Wide summer mountain village approach; old homes, cultivated hills, laundry and a roadside bicycle, no people.
0|3|M|street|narrator|刑警到女孩倒下的街道调查|Detective stands near a worn shop doorway on an ordinary town shopping street, questioning an off-frame witness; parked ambulance far behind with all markings absent. No injured person.
0|4|C|office|none|案件材料与检材进入调查|An unopened opaque evidence pouch and a closed plain medical folder on the scratched investigation desk, neither body nor anatomical content visible.
0|6|M|office|narrator|刑警独自回想这起案件|Detective alone at desk after dark, tense tired gaze downward at the closed folder, amber lamp and cold window.
1|0|M|home|linna+grandpa|女孩与爷爷共同生活|Ordinary summer afternoon memory: fully clothed thirteen-year-old girl sits at home doing homework; grandfather sits beside window with a farming hat, respectful everyday scene.
1|5|E|station|none|警方立案成立专案组|Wide empty county police meeting room, chairs around a long table, open plain folders and enamel cups, unmarked door and cabinet.
1|9|M|meeting|narrator+feng|办案人员听取法医报告|Two detectives listen gravely across meeting table toward an off-frame adult speaker; medical folder closed in foreground, no body, no anatomical charts.
1|12|C|meeting|none|尸检材料提示女孩曾受伤害|Closed plain forensic report with an opaque sealed pouch beside it on the meeting table; only ordinary stationery and desk lamp, no injury, no anatomical content.
1|15|C|lab|none|检材与时间范围成为侦查线索|Evidence laboratory bench with two securely capped plain sample tubes in a small rack and a sealed paper envelope; no bodily material visible, no lettering or graphics.
2|2|M|interview|grandpa+narrator|爷爷讲述自己务农未见孙女|Grandfather sits with farming hat resting on knees opposite younger detective in interview room, lined face tired, natural seated conversation.
2|5|C|interview|grandpa|爷爷捂脸回答管不了孙女|Grandfather close face and work-worn hands covering his brow, brown cotton sleeves, hat on knees partly visible, grief rather than theatrical screaming.
2|7|E|village|none|村庄只剩老人孩子生活的痕迹|Empty village courtyard, small schoolbag beside an older straw farming hat on two stools, laundry under eaves and cultivated field beyond.
2|11|M|home|grandpa|爷爷独自守着简单饭桌|Grandfather alone at a small table set with two rice bowls, opposite chair empty, evening window light, no girl in frame.
2|14|M|interview|narrator+grandpa|问询仍无法确定女孩行踪|Detective looks down at a plain notebook while grandfather shakes his head across table; no accusation gesture.
2|15|C|lab|none|采样材料被单独登记保存|Plain sealed sampling envelope beside unused cotton swab packaging and a capped tube on a scratched work tray; no person or visible biological material.
2|18|E|station|none|调查继续围绕熟人关系展开|Empty station corridor receding past closed interview-room door; foreground desk corner has plain closed case folder, no people, no writing.
2|20|C|office|none|爷爷的比对结果进入案卷|Two plain document folders set separately on desk with sealed sample pouch between them, a ruler and pencil, no fabricated chart or readable result.
3|2|E|village|none|警方来到好友家走访|Exterior of another lived-in village courtyard, small travel bag by threshold and a pair of adult shoes near a plastic stool; no people.
3|5|M|zhanghome|zhangli+caoshan+narrator|女孩在母亲陪同下接受问询|Fourteen-year-old girl fully clothed in loose blue cotton shirt and dark trousers sits head lowered; her mother close beside her; detective across table at respectful distance.
3|6|C|zhanghome|none|好友手机成为邀约线索的载体|Ordinary dark-screen smartphone beside plain notebook on low household table, chipped enamel cup and worn table edge.
3|7|M|street|linna+zhangli|两名女孩曾结伴出门游玩|Summer daylight memory, two fully clothed young teenage friends walking beside ordinary town storefronts; Linna smiling naturally, her friend listening; no adults following.
3|11|M|zhanghome|caoshan+zhangli+narrator|母亲抢先阻断关于交往对象的问询|Mother turns sharply toward detective, hand lifted in a restrained interrupting gesture, daughter draws her shoulders inward beside her, no physical contact.
3|16|C|zhanghome|zhangli|女孩低头回避回答|Close three-quarter portrait of fully clothed teenage friend looking down and away, uncertain eyes, plain blue shirt collar visible, no glamor styling.
4|1|E|village|none|村巷成为流言传播的空间|View from the Zhang courtyard threshold down narrow lane, plastic stools clustered beside a wall and drying laundry, no people.
4|7|M|village|narrator+villagers|村民主动上前评论女孩|Detective listens as one older village woman in muted plum cotton blouse speaks from beside the courtyard door; two other adults nearby, conversational small gestures.
4|9|M|village|villagers|村民围拢议论却缺乏依据|Five adult villagers cluster naturally in lane, judging expressions and quiet conversation, uneven spacing, no child or known perpetrator present.
4|10|C|village|narrator|刑警追问后等待具体线索|Detective in close three-quarter view looking past camera toward villagers with a patient questioning expression, plain notebook held low, no dramatic pointing.
5|1|E|school|none|女孩就读镇上的寄宿学校|Wide modest town middle-school courtyard in summer, empty walkway toward classroom building, worn railings, school desks faintly visible, no lettering or signs.
5|4|M|schooloffice|teacher+narrator|班主任向刑警说明女孩情况|Middle-aged female teacher with rectangular glasses sits at desk opposite detective; restrained weary expression, exercise books stacked at one side.
5|10|C|schooloffice|teacher|老师递出女孩的自我介绍|Teacher's navy-cuffed hand offers one plain sheet turned partly away over the desk, upper torso partly visible; no readable writing, no invented portrait on sheet.
5|14|E|classroom|none|学校与家庭的引导缺口留在日常空间|Empty classroom with scuffed desks, a closed blank exercise book and pencil case on one desk, plain dark board with no writing.
5|17|M|schooloffice|narrator+teacher|警方依据老师提供的信息继续排查|Detective holds a closed plain notebook while listening to teacher, her finger rests near an unmarked sheet on desk, no list of fabricated names.
5|19|E|restaurant|none|午间餐馆也是议论传播的地方|Modest town noodle restaurant interior, worn square tables, stacked bowls, thermos at service counter, no people or menu lettering.
5|22|M|restaurant|narrator+liujia|刑警注意到收银台前的女人|Detective in left foreground half turned toward a middle-aged woman standing at far counter; she wears navy blouse and carries plain brown handbag, adult diners only as indistinct background.
5|25|C|restaurant|none|餐桌上的饭菜被调查打断|Two partly eaten noodle bowls and plain chopsticks on scratched restaurant table, dark-screen phone nearby, counter visible beyond, no people.
5|27|M|restaurant|liujia|女人听到议论露出嫌恶|Middle-aged woman beside restaurant counter in three-quarter view, lips compressed and eyes turning away with visible disdain, no exaggerated villain smile.
6|1|C|restaurant|narrator|来电打断刑警上前询问|Detective's light-blue cuff and hand holding a dark-screen phone close to his ear; restaurant counter edge and bowl beyond.
6|3|E|hospital|none|母女去过医院|Empty ordinary hospital corridor, closed examination-room door, two waiting chairs and a plain closed report folder on seat; no patient, no examination shown.
6|9|M|stationlobby|caoshan+zhangli+narrator|母亲在大厅失控女孩沉默站旁|Mother seated low on waiting bench visibly upset, fully clothed daughter standing rigidly beside it; detective approaches with an open calming hand. No exposed shoulder, no assault.
6|14|C|stationlobby|zhangli|女孩坚持自己的说法|Close portrait of fully clothed teenage friend, chin raised slightly and guarded expression, shirt fastened normally, no adult partner, no physical contact.
6|19|M|interview|feng+zhangli|女孩面对问询保持沉默|Older detective at table rubs his forehead while teenage girl sits across him looking down; respectful separation, no threatening gesture.
6|20|C|office|none|技术资料被送进调查室|A fresh plain folder resting on top of a closed laptop on scratched desk, ordinary capped pen and evidence pouch, no visible messages.
6|22|M|interview|zhangli+narrator|女孩开始配合林娜案的询问|Teenage girl calmly answers younger detective across table, both seated, mother's plum sleeve at frame edge only if needed but no additional person required.
6|25|C|lab|none|五份比对材料没有指向检材来源|Five distinct sealed opaque sample envelopes laid in a row beside one separate closed case folder; no people, no test graphics or readable identifiers.
7|3|M|office|feng+narrator|队长要求恢复手机数据|Older detective points to dark-screen phone on desk while younger detective listens, both concerned, closed computer beyond.
7|4|C|office|none|被删除记录由技术资料承载|Dark-screen smartphone connected by cable to closed plain laptop beside a stack of recovered-data papers turned face down; no private photos, no messages, no UI.
7|7|M|interview|zhangli+caoshan|母女再次面对调查资料|Teenage girl and mother sit side by side at interview table, closed folder in foreground; both fully clothed and separated from any adult man.
7|8|C|home|none|廉价化妆品留在女孩房间|Small cluster of generic unbranded capped lipsticks, face-powder compact closed, comb and school exercise book on worn bedroom desk; no person.
7|12|M|interview|caoshan+zhangli|母女围绕钱与生活发生争执|Mother turns toward daughter with pained face, daughter sits upright defending herself, hands held separately, no violence or exposed clothing.
7|16|M|interview|caoshan|母亲听完女儿的话瘫坐椅背|Mother alone seated leaning back with tears and exhausted shoulders, empty place edge nearby, no melodramatic open mouth.
7|20|E|interview|none|争执结束房间陷入沉默|Wide interview-room table detail with untouched water cups and closed notebooks, two chair backs foreground, no people; no new evidence.
7|24|M|interview|zhangli+narrator|女孩提供年长男人的住址线索|Teenage girl looking up to answer detective across desk, calm but hesitant, no depiction of the man or past encounter.
7|27|E|liuhome|none|警方找到那处住所|Exterior of an older town apartment doorway, plain wooden door partly open, well-used doormat and umbrella in corner, no people or door number.
8|4|M|liuhome|liujia+narrator|开门女人就是餐馆见过的刘佳|Same navy-bloused woman with brown handbag stands in doorway facing detective outside, familiar face, restrained displeasure.
8|6|M|shop|liuyang+linna|老人替女孩赔付打碎的商品|Respectful everyday memory in small general-goods shop: elderly teacher pays off-frame shopkeeper while fully clothed girl stands at a distance looking worried; broken ceramic trinket pieces on counter, no injury.
8|9|E|liuhome|none|老人独居的房间保留教书生活痕迹|Wide empty modest living room with one reading chair, shelf of plain books, desk with exercise book and two tea cups, slippers by threshold.
8|11|M|classroom|linna|女孩曾重新认真学习|Fully clothed thirteen-year-old girl sitting alone in classroom desk row, writing in exercise book, ordinary school-life scene, no adults present.
8|14|M|liuhome|father+liuyang|父亲向老人提出指控|Father in faded khaki workshirt stands beside doorway speaking sternly toward elderly teacher seated farther inside, no girl in frame, no physical confrontation.
8|15|C|liuhome|none|二十万元纠纷留下转账材料|Closed plain bankbook, an unmarked transfer-document folder and unlit phone on household table, enamel cup and book shelf behind, no cash pile.
8|17|M|liuhome|narrator+liujia|刑警追问为什么接受赔偿|Detective listens to navy-bloused woman across low table, his open notebook near hand, she leans back defensively.
8|22|C|liuhome|liujia|刘佳解释自己对名声与前途的顾虑|Close restrained portrait of middle-aged navy-bloused woman speaking with brittle certainty, hands clasped low, worn sofa back visible.
9|4|E|liuhome|liuyang|退休老师回到家门口|Wide view through hallway toward elderly teacher entering his home with a small cloth grocery bag; doorway and shelves dominate, detective only off-frame.
9|7|M|interview|liuyang+narrator|老师首先肯定女孩是好姑娘|Elderly teacher seated across younger detective in interview room, kind sorrowful eyes, cloth grocery bag by chair leg, no girl.
9|10|C|interview|liuyang|老师讲述女孩拒绝诬陷他|Close elderly teacher face speaking gravely, grey eyebrows and square glasses, grief without theatrical expression; no reconstruction of violence.
9|14|E|liuhome|none|家门内的争端没有传到外界|Closed apartment wooden door viewed from empty hallway, worn doormat and umbrella in corner, no people or violent aftermath.
9|17|M|liuhome|liujia+father|父亲与刘佳以金钱封住纠纷|Navy-bloused woman and khaki-workshirt father sit apart across low table, closed transfer folder between them, guarded adult conversation; no girl or physical abuse.
9|18|M|liuhome|linna+liuyang|女孩向帮助过自己的老师道歉|Fully clothed girl standing by elderly teacher's study doorway with head lowered respectfully, teacher seated at desk looking gently toward her; generous distance, no touching.
9|20|E|liuhome|none|女孩曾学习的位置如今空着|Empty study chair next to a closed school exercise book and sharpened pencil on worn desk, reading glasses folded nearby, cool window and dim warm lamp.
9|22|C|lab|none|老师的样本比对同样不匹配|A new sealed opaque sample envelope and closed report beside original case folder, distinct positions and plain stationery, no readable results or fabricated DNA graphic.
10|5|M|station|liuyang+narrator+feng|老师离开前请求警方还女孩公道|Elderly teacher bows slightly to two detectives at corridor doorway, cloth grocery bag at his side; detectives stand respectfully upright.
10|8|E|interview|none|父亲再次被传唤到讯问室|Wide empty interview room with one lone chair across desk, closed plain folder and two water cups, door ajar, no people.
10|13|M|interview|father+narrator|父亲试探警方掌握了什么|Father seated stiffly opposite young detective, forced small smile and tense eyes, khaki short-sleeved workshirt, separate hands visible on knees.
10|19|C|interview|father|父亲用侮辱女儿的话为指控辩解|Father close three-quarter face speaking defensively with hardened eyes, no grin, natural middle-aged face and short receding hair.
10|25|M|interview|father+narrator|父亲把名声与彩礼放在女儿之前|Father raises one hand in denial while detective watches in restrained anger across desk; no girl, no weapons.
10|28|C|interview|feng|队长克制愤怒追问二十万元|Close older detective face and tense clasped hands resting on desk, plain dark shoulder tabs and enamel cup at edge.
10|32|M|interview|father|父亲移开目光谎称钱存起来了|Father sits turned slightly away, eyes lowered toward chair arm, fingertips fidget at worn trouser seam; no money in frame.
11|1|C|office|none|银行流水显示款项很快转出|Plain bank ledger pages turned away beside unlit phone and sealed document envelope on desk, no numbers, account details or charts.
11|2|E|casino|none|资金去向指向C城赌场|Empty backroom gaming table in a worn city venue, plain unmarked playing-card backs face down, plastic stools and thermos, no people or gambling instructions.
11|6|M|interview|father+feng|父亲承认用赔偿款还赌债|Father answers older detective across desk with defiant face and shoulders set, one closed file on table.
11|10|E|village|none|父亲那次回村没有日常事务解释|Empty village lane with bus stop shelter and an old travel bag placed by courtyard threshold, fields beyond, no bus or person.
11|12|C|home|none|家庭工资与生活支出成为调查背景|Worn household ledger closed beside plain bankbook and an empty coin purse, enamel cup on table, no numbers or text.
11|15|M|office|narrator+feng|两名刑警对照父女的出行材料|Two detectives compare two separate plain travel-record folders on desk, fingers indicate different pages but no text or invented map.
11|17|E|stationplatform|none|父女多次跨城往返留下疑点|Empty railway platform with station benches and a suitcase at edge, distant passenger train, all signs absent, no people.
11|19|C|office|narrator|刑警意识到父亲可能利用女儿获利|Detective close face looking from one file toward another off-frame, restrained dawning concern, no written revelation.
12|4|M|interview|father+narrator|父亲在质问中反而露出笑意|Father looks up across desk with thin challenging smile while younger detective sits stiffly opposite, no caricature villain face.
12|7|C|interview|father|父亲用躲债与教育女儿搪塞|Close father's face and one palm spread on desk in self-justification, short receding hair, khaki collar, no child present.
12|9|E|interview|none|讯问双方的冲突逼近失控|Low wide view of scratched interview table with chairs on opposite sides, a closed file pushed near edge, wall-mounted camera unlit; no people.
12|13|M|interview|feng+narrator+father|年轻刑警拦住愤怒的队长|Older detective partly risen and leaning forward toward seated father; younger detective stands between their chair edges with open hand on older colleague's forearm, no blow, no raised weapon.
12|16|M|station|father+feng|父亲离开警局还劝警方别查|Father stands near exit facing older detective with dismissive half-smile and hand lowered at his side, no friendly handshake.
12|17|C|station|feng|队长对父亲的态度极其愤怒|Older detective close face at station doorway, tense jaw and brows, controlled anger, no caricature veins.
12|20|E|stationplatform|narrator+feng|两名刑警乘车前往C城调查|Wide railway platform, two detectives small in frame walking toward passenger train carrying modest overnight bags, scene and train dominate, no readable signs.
13|1|M|factory|narrator+feng+workers|工厂员工不愿提供具体情况|Two detectives question two adult factory workers in worn blue workwear beside silent workshop entrance; workers look away, no teenage worker.
13|2|C|factory|none|工厂提供考勤与来访登记材料|Plain attendance ledger and visitor folder opened with pages turned away on scratched factory desk, pencil and chipped mug, no readable writing.
13|3|E|casino|none|调查从工厂转向赌场|Empty view through a narrow doorway into worn gaming backroom with square table, plain chair backs and unmarked cards, no people.
13|6|M|casino|narrator+feng+manager|赌场人员拿出账本应对询问|Adult backroom manager in grey polo slides one plain ledger across table toward two detectives, wary neutral expression, no money changing hands.
13|11|C|casino|none|账本没有提供新的资金线索|Plain ledger closed on gaming table beside two untouched enamel cups, one face-down card at distant edge, no graph or text.
13|13|C|office|none|仅查到一通电话与二百元红包|Dark-screen smartphone beside a plain printed-record folder and unmarked payment envelope on desk, no visible amount or phone interface.
13|16|E|office|none|案卷逐渐积灰调查陷入停滞|Wide empty office shelving with plain case folders, one recessed folder has fine dust along top edge, desk lamp off, scuffed floor and enamel mug.
13|19|M|office|narrator|刑警仍在追踪父亲账户|Detective alone at desk reading a plain account folder beside closed laptop, tired but focused, cool evening light.
13|23|E|office|none|等待数月仍没有突破|Empty office after dark, half-full thermos cup and closed case folder remain on desk, rain streaks at window, no calendar text or seasonal jump markings.
13|26|M|office|narrator|刑警迟迟不愿将案子视为未破命案|Detective seated before dark computer monitor, hands still on closed folder rather than keyboard, weary profile under lamp, no screen writing.
14|3|M|stationlobby|mother+narrator|母亲除夕雪夜来到警局自首|Winter station lobby: middle-aged mother in burgundy padded jacket over grey blouse stands shaken just inside entrance, a few restrained dark maroon stains on outer sleeves, no wounds; detective turns toward her, snow outside.
14|5|E|winterhome|none|警方来到父母过年的住所|Wide view from open home doorway into modest winter living room, worn sofa, low dining table and abandoned bowls, no body or visible injury.
14|8|C|winterhome|none|现场凶器与遗留物进入勘查|Unused-looking kitchen cleaver lying flat on floor near sofa leg, not held by anyone; a fallen plain glass bottle and overturned slipper nearby, no blood, body, wound or weapon action.
14|10|M|interview|mother+narrator|警方准备听母亲解释真相|Winter-clothed mother sits across younger detective at interview desk, hands clasped tightly, eyes red and exhausted, no visible wound.
15|1|C|interview|mother|母亲说明丈夫酒后亲口透露罪行|Close mother face speaking in disbelief and grief, burgundy padded collar, grey blouse, hair loosely tied back; no reconstruction of violence.
15|4|E|factory|none|夫妻日常在同一处工厂务工|Empty modest workshop entrance beside a lunch table with two enamel lunch tins and worn work gloves, ordinary small factory, no people.
15|7|M|casino|father|父亲最初沉迷赌场的小赢小输|Father sits alone at gaming table looking down at face-down cards, one small pile of plain unmarked chips, hungry concentration, no betting instruction or numbers.
15|9|C|casino|none|赌债与借款逐渐压住父亲|Plain closed debt ledger and several small unmarked cards scattered beside empty wallet on worn tabletop, no loan contacts or text.
15|13|M|casino|father+chen|父亲与赌场老板发生联系|Two adult men standing far apart near gaming-room doorway: khaki-workshirt father listens to dark-suited middle-aged boss, serious adult conversation, no girl or exchange shown.
15|15|E|hospital|none|父亲带女孩去过医院检查|Empty hospital waiting area with two linked seats, a closed blank folder and schoolbag beside chair, no child, no examination or anatomical content.
15|18|E|hotel|none|父亲把女儿带到C城造成无法挽回的伤害|Empty ordinary hotel corridor with closed plain door, small wheelie suitcase near wall and a switched-off ceiling light; no people, beds, drinking vessels or drug paraphernalia.
15|22|M|liuhome|linna|女孩在医院检查的提议面前沉默|Fully clothed teenage girl sitting alone on study chair in elderly teacher's home, face lowered toward her school exercise book, respectful distant camera, no adults or physical contact.
15|24|C|casino|none|还清利息后父亲仍背负本金|Closed plain debt ledger at near edge of gaming table, a separately closed transfer folder farther back, no written sums or fabricated accounting diagram.
15|28|M|liuhome|father+liujia|父亲利用刘家对名声的担忧勒索|Khaki-workshirt father faces navy-bloused middle-aged woman across low table, closed plain folder between them; adult guarded negotiation, no girl.
15|32|C|liuhome|liujia|刘佳把女孩的否认误读成串通|Close navy-bloused woman listening with disbelieving eyes and compressed lips, worn bookcase background, no girl or violent event.
15|34|M|home|father|父亲继续为自己的行为找借口|Father alone in village home doorway speaking toward an off-frame listener, self-satisfied dismissive face, hands low, no girl present or physical contact.
15|35|E|stationplatform|none|父亲此后反复安排女孩去C城|Empty intercity railway platform with schoolbag on bench beside a small travel case, arriving train beyond, no people, no visible destination sign.
15|38|M|casino|chen+manager|老板通过信任的人口头传话|Dark-suited middle-aged boss speaks quietly to grey-polo adult manager near a closed gaming-room office door, separated from all young people, no phone in use.
15|41|C|office|father|父亲用电话安排那次见面|Only adult father's khaki-cuffed hand holding a dark-screen phone at an ordinary work desk, closed plain bankbook nearby, no screen details or messages.
15|42|C|home|none|那笔红包后来变成女孩购买的口红|One generic unbranded lipstick in dark casing beside its plain closed box and a face-down purchase receipt on a worn bedroom table; no person or brand logo.
15|45|M|interview|father|父亲在女儿死后选择隐瞒|Father seated alone before interview table, guarded eyes turned away from a closed case folder, tense mouth, no other actor.
15|48|E|casino|none|两百万元被藏在赌场|Empty backroom with an opaque closed metal cash box under desk, plain ledger on top, no exposed cash, readable numbers or person.
15|52|M|casino|father|父亲有钱却不敢公开使用|Father stands near closed cash box in casino backroom looking frustrated, hands in trouser pockets, no money-counting action or extra person.
15|54|E|winterhome|none|年夜饭摆在寒酸的家中|Empty winter living room, worn sofa cushion with sunken patch, old television dark, small table with two sets of bowls and a simple family meal, slippers by sofa.
15|56|M|winterhome|father+mother|父亲喝酒母亲仍惦记女儿|Father seated on sofa holding a plain bottle low; mother beside dining table looks toward one simple dish with tearful eyes, both winter layers, no child.
15|58|C|winterhome|none|摔碎的酒瓶标志真相被揭开|Broken plain glass bottle on floor beside worn sofa leg and dining-table chair; no people or blood, glass pieces confined to one small area.
16|1|M|interview|mother|母亲悲愤地讲述丈夫只惦记钱|Winter-clothed mother at interview desk, red-rimmed eyes and clenched clasped hands, no weapon, no violent action.
16|3|E|winterhome|none|杀夫经过留在空屋与遗留物中|Wide empty winter living room from hallway, dining chair pulled away, worn sofa partly blocked by doorframe, a low table and abandoned bowls; no people, no body or wound.
16|5|C|winterhome|none|反复砍杀不直接展示|Kitchen doorway foreground with cleaver resting flat on a low surface and damp folded dishcloth, unlit stove beyond; no person, action, stain or injury.
16|6|E|snowstreet|mother|母亲独自走进雪夜|Wide snowy lane after dark, mother in burgundy padded jacket small in right third walking away toward distant station light, hands lowered and empty, restrained small outer-sleeve maroon stains, no wound or weapon.
17|0|C|interview|mother|母亲为多年未能陪伴女儿自责|Close mother grieving face in interview room, tied-back hair loosened at temples, burgundy padded collar and grey blouse, no exaggerated scream.
17|2|M|home|mother|母亲曾在工作地给女儿打电话|Summer memory: mother in grey blouse alone at a small work-dorm table holding dark-screen phone to ear, two enamel lunch tins and folded work clothes, no girl in frame.
17|4|M|interview|mother|母亲掩面痛哭|Winter-clothed mother seated leaning forward with both hands covering face, shoulders slumped, untouched water cup in foreground.
17|5|C|lab|none|新的DNA比对与住宿材料印证供述|One sealed opaque sample envelope beside a closed forensic folder and separate closed hotel-record folder on lab desk, no text, DNA diagram or visible biological material.
17|6|E|office|none|调查终于完成证据闭环|Wide empty investigation desk with three plain closed folders neatly grouped beside an unlit phone and enamel cup, cool dawn and one warm lamp.
17|8|E|court|none|案件进入法院判决阶段|Empty modest Chinese courtroom viewed from back row, dark wooden benches and raised judicial desk, plain walls with NO emblem, inscription, text or graphic, solemn daylight.
17|9|M|office|narrator|刑警仍在夜里想起女孩|Young detective alone at office window after dark, closed case folder held at waist, profile visible, no fictional photo or memorial.
17|12|E|classroom|none|女孩再也无法回到日常生活|Empty classroom desk by window, closed exercise book and pencil case left on desk, cool morning daylight, ordinary summer trees outside, no ghost or memorial photo.
17|15|C|home|none|结尾回到女孩留下的生活痕迹|Close plain school exercise book and worn pencil beside unbranded capped lipstick on household desk; foreground scratched wood, window light, no text, flower metaphor, person or new event.
'''

CHARACTERS = {
 'narrator': 'Chinese male detective aged 28, lean build, short straight black hair, narrow oval face, straight eyebrows, dark brown eyes, light blue short-sleeved police shirt with plain dark shoulder tabs, charcoal trousers and black shoes. No readable badge, no lettering, no numbers.',
 'feng': 'Chinese male detective aged 48, stocky build, square face, short black crew cut with grey temples, heavy brows, light blue short-sleeved police shirt with plain dark shoulder tabs, dark grey trousers and black shoes.',
 'linna': 'Chinese schoolgirl aged thirteen, ordinary youthful face, straight black hair in a low ponytail, no makeup, loose pale mint short-sleeved cotton T-shirt, straight dark blue jeans and plain white sneakers. Fully clothed, ordinary age-appropriate everyday appearance, no jewelry.',
 'zhangli': 'Chinese schoolgirl aged fourteen, round youthful face, straight black shoulder-length bob with full fringe, loose dusty blue short-sleeved cotton shirt buttoned normally, dark grey straight trousers, white sneakers. Fully clothed, no makeup or jewelry.',
 'grandpa': 'Chinese grandfather aged seventy, thin build, deeply lined narrow face, short grey hair, faded brown cotton short-sleeved shirt, charcoal loose trousers, black cloth shoes, old straw farming hat carried in hand.',
 'caoshan': 'Chinese woman aged forty, sturdy build, round face, black hair in a practical short ponytail, muted plum cotton short-sleeved blouse, plain dark trousers and black flat shoes, no jewelry.',
 'teacher': 'Chinese female middle-school teacher aged forty-four, lean build, long oval face, rectangular black glasses, short black bob tucked behind ears, plain navy cotton shirt and grey trousers, black flat shoes.',
 'liujia': 'Chinese woman aged forty-two, slender build, angular face, black hair tied in a low neat bun, navy short-sleeved blouse, brown trousers, black flat shoes, plain brown handbag.',
 'liuyang': 'Chinese retired male teacher aged sixty-eight, slim build, kind lined oval face, thinning short grey hair, thin square silver glasses, light grey summer cardigan over off-white cotton shirt, charcoal trousers and brown cloth shoes.',
 'father': 'Chinese male factory worker aged forty-one, medium build, broad face with a receding short black haircut, faint stubble, faded khaki short-sleeved workshirt, dark brown trousers and black work shoes.',
 'mother': 'Chinese female factory worker aged forty, lean build, tired long face, black hair tied low, plain grey cotton blouse and dark trousers, black flat shoes. Winter state adds a burgundy padded jacket over the same blouse; face and hair remain unchanged.',
 'chen': 'Chinese man aged fifty, heavy-set build, broad square face, neatly combed black hair with slight grey temples, plain charcoal suit jacket over dark blue open-neck shirt, dark trousers and black shoes.',
 'manager': 'Chinese man aged forty-five, medium build, short cropped black hair, narrow face, plain grey polo shirt and dark trousers.',
}
GENERIC = {
 'villagers': 'Several adult Chinese village residents aged forty to sixty-five, different muted cotton summer clothing, natural asymmetric group and varied faces; no child.',
 'workers': 'Two adult Chinese factory workers aged thirty-five to fifty in worn navy workwear, distinct faces, no one matching the father.'
}


def build():
    original = (EP / 'story/script.md').read_text()
    parts = re.split(r'(?m)^(\d+)\.\s*\n', original)
    sections = {0: [x for x in parts[0].splitlines() if x.strip()]}
    for i in range(1, len(parts), 2):
        sections[int(parts[i])] = [x for x in parts[i+1].splitlines() if x.strip()]
    consumed = {n: 0 for n in sections}
    halves = {'上集': [], '下集': []}
    rows = []
    for line in DATA.strip().splitlines():
        fields = line.split('|', 6)
        sec, end = map(int, fields[:2])
        typ, scene, cast, fact, visual = fields[2:]
        begin = consumed[sec]
        assert end >= begin and end < len(sections[sec]), (sec, begin, end)
        cue = '\n'.join(sections[sec][begin:end+1])
        consumed[sec] = end + 1
        part = '上集' if sec <= 9 else '下集'
        ids = [] if cast == 'none' else cast.split('+')
        shot = dict(id=f'S{len(rows)+1:03}', part=part, section=sec,
                    paragraphs=[begin,end], cue=cue, shot_type=typ, scene_id=scene,
                    cast=cast, character_ids=ids, has_character=bool(ids),
                    closeup_part='face' if typ=='C' and ids else 'prop' if typ=='C' else 'none',
                    view_angle='three-quarter', fact=fact, visual=visual,
                    line='悬疑', step='single' if not ids else 'composite',
                    character_closeup=bool(ids and typ=='C'), hands_visible=bool(ids),
                    evidence_id=f'E-{sec}-{begin}' if typ=='C' and not ids else '',
                    subject_class='character' if ids else 'prop' if typ=='C' else 'environment',
                    push_ratio=.095 if typ != 'C' else 0, needs_2048=False,
                    motion='affine' if typ != 'C' else 'static',
                    reference_roles='场景参考固定地理结构；人物参考固定身份；姿态和状态以本镜为准',
                    time_stage='除夕冬季' if sec in [14,16] or sec==17 else '夏季与调查回忆',
                    character_state='按本镜动作、季节与剧情状态，不添加未发生伤害',
                    environment_state='日常使用磨损，完整建筑，不废墟化',
                    preserve='人物年龄、脸型、发型、衣服主色、既定物件与剧情揭示顺序',
                    avoid='画内文字、暴露、侵害或砍杀过程、血腥伤口、超自然元素、空降证据')
        # Deliberate reframing, preserving the same subjects, action and narration.
        scales = {'S011':'M','S027':'M','S031':'M','S035':'M','S042':'M',
                  'S043':'E','S048':'E','S053':'M','S068':'M',
                  'S075':'E','S080':'M','S084':'M','S086':'M','S090':'M',
                  'S100':'M','S111':'M','S125':'M','S136':'M','S139':'M'}
        if shot['id'] in scales:
            shot['shot_type'] = typ = scales[shot['id']]
            shot['visual'] = re.sub(r'(?i)\bclose\b', 'medium', shot['visual'])
        framing = {'E':'Establishing wide composition: room or exterior geography dominates; any named people remain small but naturally proportioned, with the specified action visible.',
                   'M':'Medium composition: show the named people from waist or knees upward with a readable part of the room; for a people-free shot, show the object in its immediate table or doorway context.',
                   'C':'Close composition: the specified face, hand or evidence object occupies at least half the image; preserve enough background to identify the place.'}
        shot['framing'] = framing[typ]
        shot['motion'] = 'static' if typ=='C' else 'affine'
        shot['push_ratio'] = 0 if typ=='C' else .095
        shot['closeup_part'] = 'face' if typ=='C' and ids else 'prop' if typ=='C' else 'none'
        if shot['id'] in ['S030','S037','S120']:
            shot['closeup_part']='hand'
        halves[part].append(shot)
        rows.append(shot)
    assert all(consumed[n] == len(v) for n,v in sections.items()), consumed
    def norm(t):return re.sub(r'\s','',re.sub(r'(?m)^\d+\.\s*$','',t))
    assert norm(''.join(r['cue'] for r in rows)) == norm(original)
    for part, shots in halves.items():
        frame = 0
        for shot in shots:
            chars = len(re.findall(r'[\u4e00-\u9fffA-Za-z0-9]', shot['cue']))
            duration = max(2.5, chars / 3.6)
            shot.update(visible_chars=chars, frames=math.ceil(duration * 24), start_frame=frame)
            frame += shot['frames']
            shot.update(start=shot['start_frame']/24, end=frame/24, duration=shot['frames']/24)
        obj=dict(title='林娜案'+part, fps=24, shots=shots, frames=frame, duration=frame/24,
                 text_unchanged=True, text_sha256=hashlib.sha256(''.join(s['cue'] for s in shots).encode()).hexdigest())
        (EP / f'storyboard/{part}_SHOT_PLAN.json').write_text(json.dumps(obj,ensure_ascii=False,indent=2))
        print(part, len(shots), round(frame/1440,2), 'min', flush=True)
    (EP / 'storyboard/SHOT_PLAN.json').write_text(json.dumps({'shots':rows},ensure_ascii=False,indent=2))
    (EP / 'storyboard/CHARACTER_DEFINITIONS.json').write_text(json.dumps(CHARACTERS,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    build()
