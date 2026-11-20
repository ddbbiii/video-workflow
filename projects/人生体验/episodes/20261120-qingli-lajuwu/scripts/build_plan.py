from pathlib import Path
import json,re,unicodedata
from produce import EP,ROOT,save,CHARS

# 每项明确写出在场关系，禁止生成时从旁白猜人物。
ROWS='''
M|worker|living-full|Experienced cleaner pushes the entrance door only a narrow gap; takeaway boxes visibly wedge the door from inside.
M|worker+partner|living-full|At the doorway the orange partner leans back half a step while the teal cleaner stays composed; dense waste extends behind them.
C|worker|living-full|Yellow gloved small round hand on the door edge, collapsed takeaway bags trapped immediately behind the door; no empty floor.
E|none|living-full|Doorway wide view of buried blue-grey sofa and iron bed below rear-right window; floor completely hidden by irregular waist-high rubbish.
C|none|living-full|Folding table overloaded with dozens of greasy white meal boxes, several tilting at top; dried dark soup trails on table edge.
C|none|living-full|Overflowing litter trays with recognisable brown cat feces, scattered grit, matted cat hair and black food residues beside wall.
M|worker+landlord|living-full|Purple landlord stands outside threshold speaking with teal cleaner inside; abandoned litter trays and cat-food tins visible, no cats.
M|worker|living-full|Teal cleaner calmly surveys the overwhelming intermingled heaps of food containers and dirty cat litter in this same room.
M|worker+partner|living-full|Teal cleaner tightens yellow glove cuff and looks from the rear window to the exit; orange partner waits at doorway.
M|worker+partner|living-full|Teal cleaner separates dry top-layer takeaway boxes into a nested stack; orange partner holds open a waste bag for bottles and paper.
E|worker+partner|living-path|Three tied waste sacks just outside the entrance; a small corner of the folding table has emerged, rest of room still buried.
M|worker|living-path|Teal cleaner pauses briefly beside newly exposed table corner, looking over the remaining huge heaps in the living room.
C|none|living-path|Beneath the dry boxes, wet takeaway bags adhere in one tangled mass to the floor, beads of brown liquid at split seams.
M|worker|living-path|Teal cleaner uses yellow gloves to lower a leaking takeaway bag into a second heavy black bag; large remaining waste piles behind.
C|worker|living-path|Yellow gloved hook hand beside a cracked food container wedged under cabinet foot, its broken lid and spilled scraps plainly visible.
M|partner|living-path|Orange partner holds a damp cardboard box just above floor; its soggy base folds downward and several containers remain on floor below.
M|worker+partner|living-path|Teal cleaner gestures down for orange partner to set the damaged box down, intact empty boxes stacked separately from wet cardboard.
M|worker+partner|living-path|Orange partner returns through doorway empty-handed after carrying sacks out; teal cleaner still crouches over the same sticky floor patch.
E|none|living-path|Look from corridor: several tied sacks grouped along wall clear of exit; inside doorway huge rubbish heaps still bury sofa and bed.
E|none|living-path|Repeat the original doorway angle: only a thin freshly cleared winding aisle, most floor and both furniture seats still buried.
M|worker|bedside|Teal cleaner reaches the bedside cardboard nest filled with old clothes, torn paper lining and empty cat-food bags.
C|none|bedside|Several emptied litter trays beside bed; one upside-down tray has a thick crust of dirty cat litter stuck around its bottom rim.
M|worker|bedside|Teal cleaner keeps the litter tray stationary and gently loosens clumped litter with a short scraper, yellow gloves visible, no dragging.
C|none|bedside|Close view of a thick hardened mat of cat litter, hair and fecal fragments, one scraped edge exposing dark flooring beneath.
M|worker+partner|bedside|Orange partner holds broom stopped above wet smeared litter; teal cleaner indicates a scraper instead, coated broom bristles clearly visible.
M|partner|bedside|Orange partner rests broom against wall and looks ruefully at the tiny cleared patch surrounded by heaps, shoulders lowered.
M|worker+partner|bedside|Teal cleaner indicates the bagged dry waste then the hard contamination still stuck below, explaining to orange partner with simple gestures.
E|none|bedside|Bedside boxes moved away: half the iron bed visible, a compressed sleeping hollow along wall immediately next to a cardboard cat nest.
M|worker+partner|bedside|Both cleaners shift iron bed a short distance; tangled paper and hair and food containers previously trapped underneath are exposed.
E|none|bedside|Window light reaches a newly exposed area beside bed for first time; original grey-brown floor color visible amid broad remaining stains.
E|none|kitchen-full|First kitchen establishing view: old sea-green wall tiles, dirty dishes and takeaway tubs crowd counter, sink full of opaque grey water.
E|none|kitchen-full|Second kitchen angle across narrow passage: fridge door blocked by takeaway rubbish, stove piled with boxes, no free place to step around.
M|partner|kitchen-full|Orange partner tilts damp cardboard box away from wall; a clearly visible cluster of cockroaches is exposed behind it at wall-floor seam.
M|worker+partner|kitchen-full|Damp box rests back on floor; orange partner recoils toward doorway while teal cleaner raises a small yellow stop gesture.
M|worker+landlord|kitchen-full|Teal cleaner at kitchen doorway points out insect-infested seam to purple landlord, who stands outside kitchen; no spraying or chemicals.
M|landlord|kitchen-full|Purple landlord stops two steps inside kitchen after noticing small cockroaches near sink and wall crevice; open doorway behind him.
M|worker+landlord|kitchen-full|Teal cleaner firmly indicates both rubbish heaps and the insect area, purple landlord listens from threshold; no implied complete extermination.
M|worker+partner|kitchen-cleared|Both cleaners remove empty containers from separate kitchen sections; counter partially exposed but still greasy, no miraculous cleanup.
C|none|kitchen-cleared|Newly exposed counter and cabinet bottom have heavy grease, stuck cat hair and dirt; stacks of removed containers in background.
E|worker+partner|kitchen-cleared|Narrow kitchen floor path now joins living room aisle; one cleaner carries a tied sack out, other holds the next sack ready.
M|worker+landlord|sofa-exposed|Blue-grey sofa finally visible after surface rubbish removed, still filthy and damaged; purple landlord gestures to it while teal cleaner listens.
M|worker+partner|sofa-exposed|Both cleaners clear remaining sacks in front and behind sofa to make space to move it; sofa still against wall.
C|none|sofa-exposed|Sofa shifted away from wall exposes flattened mats of hair and litter, hard brown cat feces and torn paper underneath.
M|worker+partner|sofa-exposed|Both cleaners carefully tilt the same sofa to inspect underside; broad dark stain on bottom fabric and deformed foam corner visible.
M|worker+partner+landlord|sofa-exposed|Purple landlord points uncertainly at sofa upholstery while orange partner looks at torn bottom fabric; teal cleaner studies damage.
M|worker+landlord|sofa-exposed|Teal cleaner points out a wiped surface area and the deeply stained exposed filling as different conditions to purple landlord.
E|worker+partner|sofa-removed|Both cleaners carry the blue-grey sofa out through entrance, now empty sofa footprint opens a large part of living room.
C|none|sofa-removed|Close view of empty sofa footprint: a crushed cat-food tin, several sticky clumps of hair and a dark moisture stain by skirting.
M|worker+partner|sofa-removed|Orange partner studies exposed contamination before reaching for scraper, broom remains unused against wall; teal cleaner works nearby.
M|partner|sofa-removed|Orange partner nests intact dry boxes neatly and places leaking refuse in a separate lined bag, using the learned sorting method.
E|none|floor-dirty|After midday: large loose rubbish removed, filled waste sacks visible outside threshold; brighter room exposes dirty floor, sofa absent.
M|worker+landlord|floor-dirty|Purple landlord stands in open doorway looking at now empty floor; teal cleaner kneels beside persistent crusted grime with cleaning tools.
C|none|floor-dirty|Exposed floor under former cardboard boxes has large watermarks, hardened litter around bed leg and cabinet foot; no loose rubbish piles.
M|worker|floor-dirty|Teal cleaner works one small floor patch with scraper and cloth; loosened debris in small collection tray, adjacent floor visibly sticky.
C|worker|floor-dirty|Yellow gloved hand wipes edge of repeatedly washed patch; fresh bucket and replacement cloth nearby, original floor color finally visible.
M|partner|floor-dirty|Orange partner changes a soiled pale-blue glove beside tied waste sack, jacket cuffs visibly dirtier from hours of work.
E|worker+partner|floor-partial|Wide living room with two cleaners working on adjacent sections, connected areas of clean floor expand; sofa remains absent, bed and table unchanged.
M|landlord|floor-partial|Purple landlord quietly stands beside rear-right window watching work on the floor, shoulders relaxed, no new furniture.
E|none|bathroom-full|First view through narrow half-open bathroom door: dirty clothes and empty litter sacks block doorway, drain half clogged with hair and litter.
M|worker|bathroom-partial|Teal cleaner bends low inside tiny bathroom, removed clutter collected near doorway; cleaning drain edge and dirty tiles, no loose litter into drain.
E|none|clean-room|Full room visible from entrance to rear-right window: loose waste removed, bed and table visible, sofa absent, local damaged corner persists.
M|worker|clean-room|Teal cleaner stops near former sofa location beside damaged skirting, leans down to inspect persistent dark stain after general cleanup.
M|worker+partner|clean-room|Orange partner returns with cleaning bucket; teal cleaner holds a small stop gesture and points to specific damaged wall-floor joint.
C|none|clean-room|Close view of swollen stained flooring edge and discolored cabinet foot near skirting, surrounding floor wiped clean; material damage still visible.
M|worker+landlord|clean-room|Purple landlord asks about another wash while teal cleaner indicates swollen floor edge and stained cabinet base, hands away from chemical products.
M|landlord|clean-room|Purple landlord looks across cleaned room then down at same damaged corner; room remains ordinary and worn, no completed repair.
M|worker+landlord|clean-room|Teal cleaner shows landlord cleaned floor and unrepaired corner, kitchen visible beyond still needing separate pest service, no repair crew.
M|worker+landlord|clean-room|Teal cleaner walks landlord between clean floor patch and damaged cabinet base, clearly indicating limited cleanup outcome without written labels.
E|none|clean-room|Match opening doorway view exactly: door fully opens, floor visible, same iron bed, exposed folding table and rear-right window; sofa absent.
M|landlord|clean-room|Purple landlord walks past fully exposed folding table inspecting bare tabletop and room floor, no rubbish reappears inside room.
M|worker+partner|clean-room|Both cleaners gather tools at entrance and carry final tied sacks out; orange partner removes pale-blue gloves, worn cuffs visibly dirty.
M|worker+partner+landlord|clean-room|Purple landlord speaks to both tired cleaners at threshold; cleaned room behind them contrasts with last waste sacks outside.
M|worker|clean-room|Teal cleaner checks the collected bucket, scraper and cloths, then glances back at empty former sofa position inside room.
E|none|clean-room|Room now free of loose rubbish, most floor cleaned; damaged wall corner and stained cabinet foot remain, kitchen requires further service.
M|worker|clean-room|Teal cleaner stands tired but composed at exit holding tool bucket, final look over remaining damaged area; no celebratory pose.
E|worker+partner|outside|Both cleaners place buckets and scrapers into open rear of an ordinary unbranded work van outside rental building; grouped tied refuse sacks nearby, tired postures, no text.
'''.strip().splitlines()

def main():
 s=(EP/'story/script-v1-locked.md').read_text();cues=re.findall(r'^(S\d+) (.+)$',s,re.M)
 assert len(ROWS)==len(cues)==76
 scenes={}
 stage={
 'living-full':'Morning. Same approved rental room: dark doorframe left, folding table left foreground, blue-grey sofa middle, iron bed beneath rear-right window, peeling wall corner. Overwhelming irregular food waste heaps conceal essentially all floor and sofa seat; no walking aisle.',
 'living-path':'Morning. Same rental room and furniture placements. Uppermost waste removed only near entrance and table; one narrow aisle, most waste still high and sofa and bed still buried. A few filled sacks outside door.',
 'bedside':'Late morning. Same iron bed under rear-right window and same peeling wall. Loose waste partly cleared near bed; damp cardboard cat nests and emptied litter trays, hard matted waste under bed; only half bed emerges initially.',
 'kitchen-full':'Late morning. Same cramped kitchen, sea-green tiled wall, sink under window right, fridge at left, stove and narrow passage. Greasy meal containers everywhere, cloudy standing sink water, damp wall-side box and localized cockroaches. Never change kitchen geometry.',
 'kitchen-cleared':'Late morning. Same sea-green kitchen geometry; empty containers partly removed, greasy counter and cabinet feet exposed, narrow floor passage now opens to living room. Pest issue unresolved.',
 'sofa-exposed':'Before midday. Same blue-grey sofa at same living-room position; loose surrounding food waste largely cleared, stained fabric and scratched foam; bed and folding table stay in same places, floor contamination remains.',
 'sofa-removed':'Midday. Same living room, blue-grey sofa now removed permanently, empty rectangular footprint with compressed hair, litter and crushed tin. Bed and table unchanged, floor grimy, no large loose heaps.',
 'floor-dirty':'Afternoon. Same living room, all large loose waste removed, sofa permanently absent, broad dirty floor exposed, hardened litter and sticky residues; bed and table unchanged, local clean patches only.',
 'floor-partial':'Afternoon. Same living room. Sofa absent permanently, broad contiguous cleaned floor areas expanding, one visibly dirty unprocessed section. Old peeling wall and stained corner not repaired.',
 'bathroom-full':'Afternoon. Tiny old bathroom through narrow half-open door, white-grey tiles, floor drain in back right, dirty clothes and empty cat-litter sacks block entry, hair and sand choke drain edge, dried wastewater rings.',
 'bathroom-partial':'Afternoon. Same bathroom geometry, clutter mostly removed, cleaner can enter, unwashed tiled patch and partly exposed drain edge; no magical pristine new tiles.',
 'clean-room':'Late afternoon. Match opening rental-room geometry exactly: dark doorframe left, folding table left, iron bed below rear-right window. All loose rubbish removed, blue-grey sofa absent permanently. Floor substantially cleaned; same peeling wall corner, swollen stained floor edge and cabinet foot remain unrepaired. Not newly renovated.',
 'outside':'Late afternoon. Ordinary residential rental building entrance and paved loading space, unbranded grey work van rear open, buckets and scrapers; refuse sacks grouped at collection point away from traffic, no people in environment master.'}
 shots=[];t=0
 ends={9,20,30,40,50,60,68,76}
 for i,((sid,cue),r) in enumerate(zip(cues,ROWS),1):
  kind,cast,scene,visual=r.split('|',3);ids=[] if cast=='none' else cast.split('+');n=sum(unicodedata.category(c)[0] in 'LN' for c in cue)
  frames=round((n/4.8+(.90 if i in ends else .24))*30)
  motion='static' if kind=='C' or i in [1,20,30,51,61,69,74] else ('affine_pull' if i%4==0 else 'affine_push')
  shot=dict(id=sid,cue=cue,visual=visual,fact=visual,shot_type=kind,scene_id=scene,has_character=bool(ids),cast=cast,character_ids=ids,closeup_part='prop' if kind=='C' else 'none',view_angle='three-quarter' if ids else 'front',line='人生体验',step='single',character_closeup=False,hands_visible=bool(ids),evidence_id='',subject_class='person' if ids else 'environment',push_ratio=.1 if motion!='static' else 0,needs_2048=False,environment_state=stage[scene],character_state='Workwear progressively soiled and tired after midday.' if i>50 else 'Workwear increasingly soiled during physical cleaning.',preserve='Same architecture, furniture positions, identity colors; no cats, no invented actors.',avoid='No reset of garbage, removed sofa or damaged material; no text.',motion=motion,frames=frames,start_frame=t,end_frame=t+frames,duration_s=frames/30)
  t+=frames;shots.append(shot);scenes[scene]=stage[scene]
 p=dict(title='你接手一间垃圾塞满的退租房',fps=30,frames=t,duration_s=t/30,characters=CHARS,scenes=scenes,shots=shots,note='估算时间轴，未对真实人声校准；原文76段完整保留。')
 save(EP/'storyboard/SHOT_PLAN.json',p);save(EP/'image/shot-plan.json',p)
 save(EP/'logs/authorization.json',dict(date='2026-11-20',original_thread='01a1f69a-6090-7f12-84d4-e85b31621a94',instructions=['你现在给我直接跑到出成品','保留原文，成片约9～10分钟'],scope='原文不改；按静态叙事与轻运镜制作正文和独立SRT，用户原指令授权本次连续制作至交付，审核不再作为中途等待；不产声音、片头或烧录字幕。',motion_plan='本集从首次正式分镜即选择静态与affine轻运镜；未排入I2V，不存在已排I2V镜头降级。'))
 (EP/'PROJECT_STATE.md').write_text(f'''# 《你接手一间垃圾塞满的退租房》当前状态

- 2026-11-20 已接手；用户选择保留原文，接受约9～10分钟。
- 正文76段、2597可见字；旁白检查通过。时间线 {t/30:.3f}秒，1920×1080、30fps。
- 原创虚构职业体验；老手、搭档、房东，均用B版圆头细肢人。环境沿用已认可三张小样。
- 当前阶段：角色参考及正式分镜准备；尚无成片，不声称已交付。
- 交付：正文MP4和同基名独立SRT；无音轨、无片头、无文字烧录。估算时间轴，未对真实人声校准。
- 单次授权与制作范围见 logs/authorization.json；规则版本：画风4.3、角色8.2、静帧规程2.2、色彩2.2、通道v8-new2-dklb-parallel。
''')
 print(len(shots),t,'frames',t/30,'seconds')

if __name__=='__main__':main()
