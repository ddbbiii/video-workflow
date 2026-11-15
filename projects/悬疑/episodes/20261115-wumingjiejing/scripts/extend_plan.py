import json
from pathlib import Path

episode = Path(__file__).resolve().parents[1]
path = episode / "storyboard" / "SHOT_PLAN.json"
data = json.loads(path.read_text(encoding="utf-8"))
new = [
    {"id":"S37","type":"M","scene":"night_route","cast":"linxu","fact":"林旭站在卷帘门边确认导航时，双脚仍停在原地。","visual":"林旭停在路灯下，身后的旧卷帘门映着手机冷光，他低头看屏幕，鞋尖并排没有迈步。","evidence":"静止鞋尖与手机光同时可见。"},
    {"id":"S38","type":"C","scene":"night_route","cast":"none","fact":"导航预计到达时间出现负值。","visual":"手机地图的抽象路线与一个极简时间字段，时间字段留白，预留后期叠加负数，不出现真实文字或数字。","evidence":"空白时间栏与异常地图点清晰分开。"},
    {"id":"S39","type":"E","scene":"nameless_alley","cast":"none","fact":"巷子中段没有岔路，两侧高墙夹出唯一通道。","visual":"固定机位沿巷子中段向两端看，高墙和窄排水沟将空间压成一条直通道，没有岔口。","evidence":"唯一通道和两端出口同时可辨。"},
    {"id":"S40","type":"M","scene":"nameless_alley","cast":"linxu","fact":"林旭抬头辨认巷子尽头那块熟悉的蓝色灯牌。","visual":"林旭站在巷口边缘抬头看向远处蓝色灯牌，一只手握住手机，肩膀紧绷。","evidence":"他的视线方向与远处灯牌一致。"},
    {"id":"S41","type":"M","scene":"nameless_alley","cast":"linxu","fact":"林旭从巷子尽头跨回小区入口一侧。","visual":"林旭从巷道尽头跨到熟悉的灰色地砖上，身体仍朝向巷内，背后没有可见巷口。","evidence":"鞋子跨过巷道与小区地面的接缝。"},
    {"id":"S42","type":"C","scene":"nameless_alley","cast":"none","fact":"巷子尽头的墙面封闭，没有开口通往小区。","visual":"巷子尽头墙体与排水沟相接的静物近景，墙面连续无洞口，边上有旧扫帚和裂纹地砖。","evidence":"连续墙面没有门洞或通道。"},
    {"id":"S43","type":"M","scene":"apartment_entry","cast":"linxu","fact":"林旭在单元楼下停住脚步，确认自己已回到家。","visual":"林旭站在绿色信箱旁抬头看向熟悉的单元楼，手机握在手中，门内楼梯灯亮着。","evidence":"信箱和楼梯入口共同标明地点。"},
    {"id":"S44","type":"E","scene":"bedroom","cast":"none","fact":"床与卧室门分处房间两端，门外连接玄关走廊。","visual":"从卧室门外远看整间卧室，床靠房间深处，门内侧接向窄玄关走廊，空间关系完整。","evidence":"床、门和走廊连成一条可读路径。"},
    {"id":"S45","type":"E","scene":"bedroom","cast":"none","fact":"卧室门外的走廊空无一人，尽头是玄关门。","visual":"固定机位从床边看向打开的卧室门，窄走廊通往最远处的玄关门，地面没有人影。","evidence":"空走廊与关闭的玄关门同框。"},
    {"id":"S46","type":"E","scene":"bedroom","cast":"none","fact":"玄关到床边之间没有第二条通路。","visual":"从玄关朝卧室内部看，狭窄走廊只通向床边，门框与木地板连续无侧门。","evidence":"走廊只有一条路径，墙面有旧水渍和擦痕。"},
    {"id":"S47","type":"M","scene":"bedroom","cast":"none","fact":"地图上的蓝点已经移动到玄关门口。","visual":"无字抽象地图中一个蓝色圆点沿直线移动到门口符号旁，手机边缘与旧充电线入画，不出现真实软件界面。","evidence":"圆点位置与代表门口的简化形状关系清楚。"},
    {"id":"S48","type":"M","scene":"bedroom","cast":"none","fact":"地图上的移动蓝点穿出楼栋并转向街道。","visual":"抽象无字路线图上一个蓝点从简化楼栋轮廓移出，沿线折向街道一侧，另一个点仍留在楼栋位置。","evidence":"两个点分离，移动方向从室内指向室外。"}
]
by_id = {shot["id"]: shot for shot in data["shots"]}
by_id.update({shot["id"]: shot for shot in new})
ordered_ids = [
    "S01","S02","S03","S04","S37","S38","S05",
    "S06","S07","S08","S40","S09","S10","S39","S11","S12","S41","S42",
    "S13","S14","S15","S16","S17","S18","S43",
    "S19","S20","S21","S22","S23","S24","S25","S44",
    "S26","S27","S28","S29","S30","S45",
    "S31","S32","S33","S34","S35","S46","S47","S48","S36"
]
data["shots"] = [by_id[key] for key in ordered_ids]
path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"extended and ordered {len(data['shots'])} shots")
