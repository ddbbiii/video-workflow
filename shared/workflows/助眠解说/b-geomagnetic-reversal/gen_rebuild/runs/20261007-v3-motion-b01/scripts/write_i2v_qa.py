import json,os,sys
M=sys.argv[1]
q={
"ch1-c08":("pass","仪器舱与地形稳定，云海/薄雾缓动，无闪烁"),
"ch2-c07":("pass","浪花自然，岩石与箱子稳定；交叉淡化循环"),
"ch2-c09":("reject","熔岩裂隙形状逐帧重构（主体变形），帧间差偏高(mean 6.3)"),
"ch3-c05":("reject","出现明显镜头移动（违背锁定机位），乒乓循环会来回摇晃"),
"ch3-c07":("note","有轻微机位漂移，海面月光自然；漂移幅度小，可接受"),
"ch3-c09":("reject","前景手部在片中消失（主体变形）"),
"ch4-c03":("reject","明显推镜（冰崖变大），乒乓循环会前后推拉"),
"ch5-c06":("pass","极光帘幕自然流动，人物与地形稳定"),
"ch5-c07":("reject","机位移动且前景器物/骨头重排（主体变形），帧间差偏高(mean 5.6)"),
"ch5-c08":("note","草地/鸟/云自然运动；远处动物有走动，交叉淡化循环处可能轻微重影"),
"ch6-c01":("pass","雾气缓动，小屋与小路稳定"),
"ch6-c08":("pass","云雾缓移，观测站与地面稳定"),
}
d={k:dict(verdict=v,notes=n,method="首中尾+1/4,3/4抽帧条 + 时域指标（qa/i2v_qa_part1..3.jpg/.json），人工目检") for k,(v,n) in q.items()}
p=os.path.join(M,'qa','i2v_qa.json'); assert not os.path.exists(p)
json.dump(d,open(p,'w',encoding='utf-8'),ensure_ascii=False,indent=1); print('written')
