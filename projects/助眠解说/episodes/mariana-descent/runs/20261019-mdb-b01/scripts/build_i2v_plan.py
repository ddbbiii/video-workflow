# -*- coding: utf-8 -*-
"""Build mariana-descent i2v_plan.json (36 image_to_video shots from SHOT_PLAN v1).

2026-10-20。承接 siffre-beyond-time i2v 预备件规范:
- 每镜单一温和运动(One continuous original-speed calm shot 模板);
- V5-C 循环镜 loop_allowed=True,其余 False;
- tail_extension_seconds 默认 2.5(siffre 先例);
- source_still = EP 相对路径 image/stills/<id>.jpg(已全量生成并目检通过);
- 保底验收静帧已在,失败回退 P1 affine 并记 manifest。
"""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path

EP = Path(__file__).resolve().parents[3]
PLAN = EP / "visual" / "SHOT_PLAN.json"
OUT = EP / "runs" / "20261019-mdb-b01" / "manifests" / "i2v_plan.json"

# sid -> (motion_zh, motion_reason);V5-C 镜自动 loop_allowed=True
MOTIONS = {
    # ch01
    "c1-s07": ("白色深潜器滑入水中,水花溅起后缓慢落回,水面涟漪扩散,其余静止",
               "入水瞬间=本片启程动作,水花运动需真实感"),
    "c1-s09": ("银色气泡串摇摇晃晃匀速上升,逐渐变小,水体与光柱静止",
               "气泡向上=贯穿全片的\"回得去\"母题,需真实上浮感"),
    "c1-s10": ("水下仰视,海面波纹的光斑网络缓慢晃动,气泡从画面边缘缓缓上移",
               "海面合拢=告别阳光的体感镜头,水面光影需活"),
    "c1-s11": ("深潜器保持全貌极缓下沉,上方光斑渐远渐淡,微粒缓缓下落",
               "缓降=进入深渊的定调运动,速度感必须慢"),
    # ch02
    "c2-s06": ("粉色卵球成群缓慢上升,如反向的雪,珊瑚枝轻微摆动",
               "产卵上升=本章奇观,反重力雪景需真实漂浮感"),
    "c2-s07": ("自由潜水员头朝下匀速垂直下坠,一串气泡连续上升,身体姿态稳定",
               "一口气下坠=人体剧情核心,坠落感要稳不要快"),
    "c2-s10": ("抹香鲸群垂直悬浮,仅有极轻微的呼吸性起伏与尾鳍微摆",
               "鲸垂直睡=纪念碑感,运动必须接近静止"),
    "c2-s13": ("深潜器缓缓向下穿过明暗分界线,下方水体静止,上方微光轻晃",
               "穿越界面=透光层告别的仪式感镜头"),
    # ch03
    "c3-s03": ("亿万小鱼剪影整体缓慢向上移动,队形松散不变,背景微光静止",
               "垂直迁徙=本章主事件,群体上移需持续而安静"),
    "c3-s04": ("灯笼鱼光点连成的光带缓慢漂移,光点明灭交替,水体静止",
               "光带漂移=生物光开场,循环感强(循环镜)"),
    "c3-s05": ("深潜器静止,四周鱼群剪影持续向上流动,各自匀速",
               "潜器与迁徙流交错=穿行体感"),
    "c3-s07": ("远处一点幽绿光亮起,停留,缓缓熄灭,周围微粒缓慢漂移",
               "第一枚绿光=黑暗世界的问候,明灭节奏要慢"),
    "c3-s08": ("几枚蓝色光点交替明灭,如眨眼,靛蓝水雾缓慢流动",
               "眨眼蓝点=黑暗中的生命感(循环镜)"),
    "c3-s09": ("鮟鱇鱼头顶诱饵灯轻微摇晃,大颌静止,灯的光晕呼吸般涨缩",
               "诱饵灯=本章招牌形象,摇晃要极轻"),
    "c3-s10": ("一团蓝光云从虾身喷出,在水中扩散旋转,逐渐变淡",
               "防盗警报光云=爆发但柔和的单一事件"),
    "c3-s12": ("巨口鱼眼下红光器官亮起,暗红光锥缓缓扫过黑水,鱼身静止",
               "看不见的红手电=独家奇观,光锥移动是唯一运动"),
    # ch04
    "c4-s08": ("喙鲸尾叶扬起入水,涟漪扩散,随后身影缓缓没入昏蓝",
               "鲸的深潜起点=承接上一章的动物极限"),
    "c4-s09": ("抹香鲸庞大身躯缓缓斜向下滑入黑暗,气泡串向上,速度极慢",
               "抹香鲸下潜=古老反射的巡猎,慢而沉重"),
    # ch05
    "c5-s04": ("白色海雪碎屑斜向缓缓下沉,颗粒各自飘移,背景漆黑静止",
               "海雪=午夜区口粮,持续温柔的落雪感"),
    "c5-s13": ("鲸头缓缓破开水面抬起,涟漪扩散,夜色静止",
               "互道晚安=本章情感收束,浮起动作要庄重"),
    # ch06
    "c6-s03": ("探照灯光锥亮起并缓慢增亮,白蟹群被照亮,蟹群轻微爬动",
               "灯亮瞬间=绿洲揭示的历史性时刻"),
    "c6-s06": ("管虫红色羽鳃在水流中缓慢开合摇晃,管体不动",
               "无叶之花=绿洲招牌,摇曳节奏近似花园"),
    "c6-s08": ("黑烟囱热液持续涌出,热浪扭曲闪动,周围水体缓慢扰动",
               "烟囱涌流=冰火交界奇观(循环镜,适合循环)"),
    # ch07
    "c7-s01": ("沉船船头巨影从黑暗中缓缓显形,细节逐渐可辨,推进极慢",
               "泰坦尼克登场=本章最高潮,显形速度=敬畏感"),
    "c7-s06": ("鲸尸庞大身躯缓缓下沉,腐屑轻扬,黑暗从下方漫上来",
               "鲸落开始=三十年宴席的序幕,下沉要安详不恐怖"),
    "c7-s13": ("海参群体在软泥上极缓爬行,身后的细痕缓慢延展",
               "海参爬行=平原时间感,速度接近静止"),
    # ch08
    "c8-s05": ("狮子鱼在坡前安静悬停,尾鳍与偶鳍轻微摆动,身体微幅起伏",
               "水滴身影=最后一种鱼的定装运动,轻而柔"),
    "c8-s11": ("钩虾群从坡壁各处向饵笼缓缓聚拢,步足细碎移动",
               "赶集=万米生命力的证明,聚拢要热闹而不乱"),
    # ch09
    "c9-s04": ("钢球潜水器匀速缓缓下沉,粒子从画面边缘上掠,黑暗加深",
               "五小时下沉=1960s 的耐心,匀速单调是主题"),
    "c9-s11": ("细泥雾在水中缓慢翻涌下沉,颗粒逐渐落定,光锥静止",
               "面粉泥雾=万米质感(循环镜,沉降适合循环)"),
    "c9-s12": ("一只钩虾在灯光边缘缓慢爬行,触须轻点泥面",
               "世界最深处住户=收束前的亲密凝视"),
    # ch10
    "c10-s01": ("压载物脱落下沉,泥雾腾起,深潜器缓缓离底上升",
               "抛压载=返程开始的释放感"),
    "c10-s08": ("上方蓝光层逐渐变亮变厚,水体缓缓上移,微粒向下掠过",
               "蓝回来了=全片情感转折,光要慢慢长出来"),
    "c10-s10": ("深潜器破出水面,水花飞溅发光,月光倾泻而下铺满画面",
               "破水=全片最亮一帧,水花与光必须真实而辉煌"),
    "c10-s13": ("夜浪一排排起伏推进,浪脊月光闪动,节奏安稳",
               "起风了=回到人间烟火,浪的循环推进(循环镜)"),
    # epilogue
    "e-s03": ("夜浪轻涌,月光路径在水面微微晃动,持续而安稳",
              "浪替黑暗醒着=尾声守夜意象(循环镜)"),
}

TPL = "One continuous original-speed calm shot. {}. Slow gentle motion only. No cuts, no shake, no camera move, no flicker."


def main():
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    shots = []
    for s in plan["shots"]:
        if s["shot_class"] != "image_to_video":
            continue
        sid = s["id"]
        if sid not in MOTIONS:
            raise SystemExit(f"missing motion copy for {sid}")
        motion_zh, reason = MOTIONS[sid]
        shots.append({
            "id": sid,
            "section": s["section"],
            "strategy": s["strategy"],
            "image_mode": s["image_mode"],
            "image_prompt": s["image_prompt"],
            "motion_prompt": TPL.format(motion_zh),
            "motion_zh": motion_zh,
            "motion_reason": reason,
            "loop_allowed": s["strategy"] == "V5-C",
            "tail_extension_seconds": 2.5,
            "source_still": f"image/stills/{sid}.jpg",
            "status": "planned",
        })
    doc = {
        "schema_version": 1,
        "episode": "mariana-descent",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source": "visual/SHOT_PLAN.json v1(全片 134 镜,image_to_video=36)",
        "count": len(shots),
        "notes": [
            "i2v 预备件:每镜单一温和运动,按 motion_prompt 生成;保底验收静帧已全量通过,失败回退 P1 affine 并记 manifest。",
            "引擎 LTX-2.3 distilled(与章鱼集/siffre 集同工作流参数),289 帧@24fps≈12s,1280x704,seed 42,后处理 crop+lanczos 1080p。",
            "V5-C 循环镜 loop_allowed=True(6 镜:c3-s04/c3-s08/c6-s08/c9-s11/c10-s13/e-s03)。",
            "GPU 请求: shared/gpu-queue/requests/mariana-i2v-batch-20261020.json;锁协议三路径;先 2 镜试点(c1-s09/c6-s08)合格后全量。",
        ],
        "shots": shots,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    loop_n = sum(1 for s in shots if s["loop_allowed"])
    print(f"i2v_plan: {len(shots)} shots (loop={loop_n}) -> {OUT}")


if __name__ == "__main__":
    main()
