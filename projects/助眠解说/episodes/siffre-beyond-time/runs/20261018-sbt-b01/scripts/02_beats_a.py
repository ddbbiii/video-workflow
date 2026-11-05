# -*- coding: utf-8 -*-
"""Beats part A: bridge + ch01-ch05 的 段落 -> 已有镜头ID 映射。

siffre-beyond-time 与 newton 不同:镜头(v1,135镜)已由 visual/build_shot_plan_v1.py
按大纲节拍先行定稿并在生图中;口播锁定后只需要把 NARRATION_MASTER 的段落
(audio/utterances.json 的 paragraph_id)分配到这些既有镜头上。

schema(值=既有镜头ID列表,顺序=播放顺序):
    "bridge-p01": ["brg-s01", "brg-s02"],
    "ch01-p01": ["c1-s01", "c1-s02"],
    ...

编写规则(04_build_shot_plan.py 会机器校验):
1. 正文全部段落必须连续覆盖,不得跳段;
2. 每个镜头ID只能被使用一次,全部 135 镜必须被分配(bridge/ch01..ch10/epilogue);
3. 段落的 section 必须与镜头的 section 一致(如 ch03 段落只能映射 c3-sXX);
4. 同 section 内镜头保持 SHOT_PLAN 原顺序(不回跳);
5. 允许一个段落没有镜头吗?——不允许;若段落多镜头少,优先并段或回剧本侧确认
   (镜头数 ±20% 调整无需回剧本侧,超出回信)。

2026-10-19 编排说明(NARRATION_MASTER v1.1 锁定稿,正文 203 段 vs 135 镜):
- 段落数约为镜头数的 1.5 倍(口播为助眠短句风格,大量 10-40 字连接段)。
  按 02/04 的机器校验口径,"相邻短段共镜"实现为:短/评述段取空列表 [],
  其声音落在相邻主段镜头的画面上(04 对空列表合法,est 时间轴仍全局累计)。
- 每个主段 1-3 镜:长段(>=60字,含多画面动作)拆 2-3 镜;语义对位以 SHOT_PLAN
  每镜 beat 描述为准(如 ch07-p12"数数测试"段对 c7-s09 数数自测)。
- 各章镜数:bridge3/ch01=11/ch02=11/ch03=12/ch04=12/ch05=14(part A 共63);
  ch06=11/ch07=15/ch08=14/ch09=13/ch10=12/epilogue=7(part B 共72);合计135。
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EP = HERE.parents[2]

BEATS_A = {
    # ================= bridge 故事由来(5段/3镜) =================
    # p01"这是一件真实的事"为开口号,骑乘 brg-s01;p04 契约结语骑乘 brg-s02
    "bridge-p01": [],
    "bridge-p02": ["brg-s01"],   # 63天/《超出时间》预告 <-> 黑暗里的一盏灯
    "bridge-p03": ["brg-s02"],   # 数字有出处/画面是还原 <-> 叙事契约:日记与还原
    "bridge-p04": [],
    "bridge-p05": ["brg-s03"],   # 从冰川到卧室这条线 <-> 从一点暖到整片黑

    # ================= ch01 一、一个研究石头的人,把表留在了地上(22段/11镜) =================
    "ch01-p01": [],              # 时间地点开篇,骑乘 c1-s01
    "ch01-p02": ["c1-s01"],      # 清晨公路/车/晨雾雪山 <-> 1962年出发的清晨
    "ch01-p03": ["c1-s02"],      # 清点设备样本袋记录本 <-> 行囊细节
    "ch01-p04": ["c1-s03"],      # 时间藏在石头和冰层里 <-> 冰川表面融水流
    "ch01-p05": [],              # 临时起念头(p05-p11 为决定+背景评述块,骑乘冰川/裂隙镜)
    "ch01-p06": [],
    "ch01-p07": [],
    "ch01-p08": [],
    "ch01-p09": [],
    "ch01-p10": [],
    "ch01-p11": [],
    "ch01-p12": ["c1-s04", "c1-s05"],   # 出发那天/裂隙边/蓝冰/他 <-> 裂隙+23岁剪影
    "ch01-p13": ["c1-s06", "c1-s07"],   # 摘表放石块表盘朝上 <-> 摘表关键帧+表的静物
    "ch01-p14": ["c1-s08"],      # 表和草地留在阳光里 <-> 表被留在地上
    "ch01-p15": [],              # "连光都没有"过渡句,骑乘
    "ch01-p16": ["c1-s09"],      # 头灯光锥/绳索/硬币大天光 <-> 头灯进入黑暗
    "ch01-p17": [],              # 黑暗接住了他,骑乘
    "ch01-p18": ["c1-s10"],      # 新家安顿(帐篷木桌灯罐头书) <-> 营地首夜
    "ch01-p19": ["c1-s11"],      # 特意挑的书/两个月很长 <-> 帐篷内:两个月的家
    "ch01-p20": [],
    "ch01-p21": [],              # 灯亮=第一次有晚上,骑乘章尾
    "ch01-p22": [],

    # ================= ch02 二、两台钟(14段/11镜) =================
    "ch02-p01": ["c2-s01"],      # 实验里有两台钟(开章) <-> 洞内营地全景定场
    "ch02-p02": ["c2-s02", "c2-s03", "c2-s04"],   # 电话/地面帐篷/方格纸记录 <-> 电话机+地面营地+记录员
    "ch02-p03": [],
    "ch02-p04": [],              # 齿轮vs细胞(比喻段,骑乘)
    "ch02-p05": [],
    "ch02-p06": ["c2-s05"],      # 笔尖钉在真实时刻/线是桥 <-> 记录在生长
    "ch02-p07": ["c2-s06"],      # 两份记录答案浮出 <-> 洞内:他的日记(灯登场)
    "ch02-p08": ["c2-s07"],      # 前几周一切正常 <-> 罐头与物资(秩序井然)
    "ch02-p09": ["c2-s08", "c2-s09", "c2-s10"],   # 勘测记号/锻炼影子 <-> 勘察+洞窟尺度+锻炼
    "ch02-p10": [],
    "ch02-p11": [],
    "ch02-p12": ["c2-s11"],      # 只有灯亮和灯灭 <-> 他的"夜":灯熄
    "ch02-p13": [],
    "ch02-p14": [],              # 走偏/表格往下延(章尾钩子,骑乘)

    # ================= ch03 三、数到一百二十,用了五分钟(19段/12镜) =================
    "ch03-p01": ["c3-s01"],      # 最先出问题的是时间(开章) <-> 日记:行距正常(前期)
    "ch03-p02": [],              # p02-p08 数数测试块(此章无对应镜,数数镜 c7-s09 归 ch07)
    "ch03-p03": [],
    "ch03-p04": [],
    "ch03-p05": [],
    "ch03-p06": [],
    "ch03-p07": [],
    "ch03-p08": [],
    "ch03-p09": ["c3-s02", "c3-s03"],   # 读书放下拿起/日记越估越偏 <-> 翻页+行距变大
    "ch03-p10": ["c3-s04", "c3-s05"],   # 无法验证/没人替他核对 <-> 录音机转轮+录音机话筒(空转不报时)
    "ch03-p11": [],              # "日记越写越松"单句,骑乘 c3-s03 画面
    "ch03-p12": ["c3-s06"],      # 把握不住一天多长 <-> 醒来,不知时候
    "ch03-p13": ["c3-s07", "c3-s08"],   # 洞里其实也有自己的钟 <-> 火焰盛期+腕上表痕(洞内的钟)
    "ch03-p14": ["c3-s09", "c3-s10"],   # 渗水一滴一滴落进石窝/涟漪 <-> 水滴石窝+一滴坠落
    "ch03-p15": [],              # "不报时/稳定地走"为水滴注脚,骑乘
    "ch03-p16": ["c3-s11"],      # 翻遍营地没有东西报时/磁带 <-> 空罐头(营地搜寻)
    "ch03-p17": [],              # 电话线段(此章无对应镜,线镜在 ep-s03),骑乘
    "ch03-p18": [],
    "ch03-p19": ["c3-s12"],      # 两边记录对不上(章尾) <-> 秩序仍在,黑暗更浓

    # ================= ch04 四、最难的不是寒冷,是没有尽头(16段/12镜) =================
    "ch04-p01": ["c4-s01", "c4-s02"],   # 不轻松的日子 <-> 火焰矮了+焰在衰
    "ch04-p02": ["c4-s03", "c4-s04", "c4-s05"],   # 零度/98%湿度/睡袋潮/木箱霉斑 <-> 备件将尽+湿岩壁+帐篷内侧的潮
    "ch04-p03": ["c4-s06"],      # 体温34度/思维变慢 <-> 抱膝的呼吸(剪影)
    "ch04-p04": ["c4-s07"],      # 地面医生劝中断 <-> 沉默的电话
    "ch04-p05": [],              # "他拒绝了"三字段,骑乘
    "ch04-p06": ["c4-s08", "c4-s09"],   # 电话线那头的人记在纸上 <-> 地面:凝重的核对+仍在记录
    "ch04-p07": [],
    "ch04-p08": ["c4-s10"],      # 每天一模一样/无法确定睡了多久 <-> 库存见底(日子以物资计量)
    "ch04-p09": [],
    "ch04-p10": [],
    "ch04-p11": [],
    "ch04-p12": ["c4-s11"],      # 灯成了他唯一的太阳 <-> 一点暖
    "ch04-p13": [],              # 灯亮白天灯灭夜(细述段,骑乘一点暖)
    "ch04-p14": [],
    "ch04-p15": [],
    "ch04-p16": ["c4-s12"],      # 两台钟差别越拉越大(章尾) <-> 睡去(章尾安放)

    # ================= ch05 五、你的"一天",比一天长(19段/14镜) =================
    "ch05-p01": ["c5-s01"],      # 把两份记录放在一起 <-> 纸上的竖痕
    "ch05-p02": ["c5-s02"],      # 入睡时刻连成后漂的线 <-> 记录在变厚
    "ch05-p03": [],
    "ch05-p04": [],
    "ch05-p05": [],              # 一天比24h长/半小时/说明大事(结论块,骑乘)
    "ch05-p06": ["c5-s03"],      # 身体里有自己的钟/太阳每天校准 <-> 世界的钟:昼夜轮转
    "ch05-p07": ["c5-s04"],      # 授时因子/光最强 <-> 夜空(世界侧)
    "ch05-p08": ["c5-s05"],      # 授时的手被拿走/钟按自己节奏 <-> 他的钟:灯亮起
    "ch05-p09": ["c5-s06", "c5-s07"],   # 睡醒一天天后漂/诚实地走 <-> 长觉+粉痕的间距
    "ch05-p10": ["c5-s08", "c5-s09", "c5-s10"],   # 半小时累积/漂到正午/两世界对照 <-> 表仍在走+滴水位+黑暗里的一盏
    "ch05-p11": [],
    "ch05-p12": [],              # 反复验证/地下室实验/体温激素(验证块,骑乘)
    "ch05-p13": [],
    "ch05-p14": ["c5-s11"],      # 光和钟的分工 <-> 地面的校准
    "ch05-p15": ["c5-s12"],      # 光负责校准 <-> 晨光第一线
    "ch05-p16": ["c5-s13"],      # 地面上一切准时运转 <-> 恒定的线
    "ch05-p17": [],              # 太阳爬上山脊/表一格格走(细述,骑乘晨光)
    "ch05-p18": [],
    "ch05-p19": ["c5-s14"],      # 电话就要响了(章尾钩子) <-> 章尾安放
}


def load_beats():
    """合并 A/B 两个映射表(04_build_shot_plan.py 使用)。"""
    from importlib import import_module as _im
    beats = dict(BEATS_A)
    beats.update(_im("02_beats_b").BEATS_B)
    return beats


def validate(verbose=True):
    """对照 visual/SHOT_PLAN.json 校验映射完整性,返回 (ok, 问题列表)。"""
    plan = json.loads((EP / "visual" / "SHOT_PLAN.json").read_text(encoding="utf-8"))
    shots = plan["shots"]
    by_id = {s["id"]: s for s in shots}
    beats = load_beats()
    problems = []
    used = []
    for pid, sids in beats.items():
        sec = pid.rsplit("-p", 1)[0]
        for sid in sids:
            if sid not in by_id:
                problems.append(f"{pid}: 镜头 {sid} 不在 SHOT_PLAN")
                continue
            if by_id[sid]["section"] != sec:
                problems.append(f"{pid}: 镜头 {sid} section={by_id[sid]['section']} 与段落 {sec} 不一致")
        used.extend(sids)
    dup = sorted({s for s in used if used.count(s) > 1})
    if dup:
        problems.append(f"重复使用的镜头: {dup}")
    body_ids = [s["id"] for s in shots]
    missing = [s for s in body_ids if s not in used]
    if missing:
        problems.append(f"未分配的镜头 ({len(missing)}): {missing[:16]}{'...' if len(missing) > 16 else ''}")
    # 同 section 内顺序检查
    for sec in sorted({s["section"] for s in shots}):
        plan_order = [s["id"] for s in shots if s["section"] == sec]
        rank = {sid: i for i, sid in enumerate(plan_order)}
        mapped = [(pid, sids) for pid, sids in beats.items() if pid.rsplit("-p", 1)[0] == sec]
        seq = [sid for _, sids in sorted(mapped) for sid in sids if sid in rank]
        if seq != sorted(seq, key=lambda x: rank[x]):
            problems.append(f"{sec}: 镜头顺序与 SHOT_PLAN 不一致(出现回跳)")
    if verbose:
        print(f"mapped paragraphs: {len(beats)}, shots used: {len(used)}/{len(body_ids)}")
        for p in problems:
            print("PROBLEM:", p)
        if not problems and beats:
            print("beats mapping OK")
        if not beats:
            print("(空表:待口播锁定后编排段落->镜头映射)")
    return (not problems), problems


if __name__ == "__main__":
    if not load_beats():
        print("空表(待口播锁定后编排 段落->镜头 映射);仅作状态提示,exit 0")
        sys.exit(0)
    sys.exit(0 if validate()[0] else 1)
