# -*- coding: utf-8 -*-
"""Build life-manual i2v_plan.json (36 image_to_video shots from SHOT_PLAN v1).

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
OUT = EP / "runs" / "20261024-lm-b01" / "manifests" / "i2v_plan.json"

# sid -> (motion_zh, motion_reason);本集全 V1 原生截取,无循环镜
MOTIONS = {
    # bridge 无 i2v
    # ch01 玄关
    "c1-s09": ("伞面上几颗水珠缓缓下滑,途中合并变大,布面与其他一切静止",
               "湿伞水珠=潮湿不会凭空消失的体感,慢到近乎冥想"),
    # ch02 冰箱
    "c2-s02": ("冰箱内一层极薄冷雾缓缓向下飘沉,玻璃容器与灯光完全静止",
               "开门冷雾=食物仍在变化的可见证据,只给雾动"),
    # ch03 厨房
    "c3-s02": ("清水持续匀速冲过番茄,细小水珠轻溅,水流不停,番茄基本不动",
               "流动清水=日常清洗的基本动作,水流感要真实"),
    "c3-s09": ("锅中蒸汽一缕缕缓缓升起、舒展、消散,锅体与灶台静止",
               "锅上的汽=厨房活着的呼吸,蒸汽走向要柔"),
    # ch04 清洁
    "c4-s10": ("温水匀速冲过盘碟,白色泡沫逐渐溶解、滑落,露出洁净表面",
               "泡沫散去=清洁完成的即时满足,溶解要连续"),
    # ch05 洗衣
    "c5-s02": ("滚筒缓慢转动,衣物随之轻轻翻滚,水位与泡沫平稳,无高速旋转",
               "滚筒转动=本章唯一机械运动,必须低速安稳"),
    "c5-s08": ("白衬衫在衣架上极缓地来回轻摆,摆幅很小,布料轻微起伏",
               "衬衫轻摆=晾干与空气的在场,摆动幅度要克制"),
    # ch06 空气
    "c6-s02": ("玻璃上的小水珠慢慢增大,偶有一颗滑下留下清痕,雾气边缘缓慢变厚",
               "凝结成珠=看不见的空气在工作的证据"),
    "c6-s07": ("纱帘在微风中极缓地鼓起又落下,像呼吸,节奏均匀",
               "窗帘呼吸=通风的路要留着,催眠感的核心镜"),
    # ch09 手机
    "c9-s02": ("手机屏幕的光晕在数秒内缓缓收缩变暗,直到熄灭,桌面反光随之减弱",
               "屏幕暗下去=数字生活的睡前仪式,亮度必须匀滑无跳变"),
    # ch10 睡前
    "c10-s08": ("台灯的光在数秒内缓缓调低一档,墙上的光晕柔和收缩,无闪烁",
               "灯调低了=向睡眠交棒的光线语言,缓变是红线"),
    "c10-s09": ("窗玻璃上的雨痕极缓下滑,新雨点落下的间隔变长,夜色静止",
               "雨还在落=夜的恒定底噪,几乎静止的动"),
    # 尾声
    "e-s03": ("窗上雨痕渐稀渐慢,最后一两颗水珠停驻,屋内几近全暗",
              "雨要停了=全片收束,运动走向停止"),
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
        "episode": "life-manual",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source": "visual/SHOT_PLAN.json v1(全片 106 镜,image_to_video=13)",
        "count": len(shots),
        "notes": [
            "i2v 预备件:每镜单一温和运动,按 motion_prompt 生成;保底验收静帧已全量通过,失败回退 P1 affine 并记 manifest。",
            "引擎 LTX-2.3 distilled(与章鱼集/siffre 集同工作流参数),289 帧@24fps≈12s,1280x704,seed 42,后处理 crop+lanczos 1080p。",
            "本集无循环镜(全 V1 原生截取);试点 2 镜(c5-s02 滚筒/c6-s07 纱帘)合格后全量。",
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
