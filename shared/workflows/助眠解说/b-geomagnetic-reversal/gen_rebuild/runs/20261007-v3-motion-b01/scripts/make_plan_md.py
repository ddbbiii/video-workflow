import json, re
p = json.load(open('motion_plan.json', encoding='utf-8'))
def rel(x):
    if not x: return '—'
    x = x.replace('\\', '/')
    for k in ('20261007-v3-motion-b01/', 'gen_rebuild/runs/'):
        if k in x: return x.split(k, 1)[1]
    return x
MV = {'in': '推近', 'out': '拉远', 'pan_r': '右移', 'pan_l': '左移'}
i2v = [x for x in p if x['method'] == 'i2v']
L = []
A = L.append
A('# MOTION_PLAN — 《地球的磁场会翻转》 v3 动态阶段（20261007-v3-motion-b01）\n')
A('生成：2026-10-07（UTC+8），由 `scripts/build_plan.py` 从 `motion_plan.json` 生成；只读引用旧时间轴与出图批次，不重导出/不重建时间轴。\n')
A('## 1. 输入\n')
A('- 静帧：`gen_rebuild/runs/20261007-v3-stills-b01/selected.json`（63 镜，43 pass / 20 note / 0 redo）')
A('- 旧口播时间轴（只读）：`edit/draft_dof_vo_v4/`（`ch1-6_dof_vo_v4.mp4` 1397.0s，`inventory.json` 63 镜 `out_dur`，`shots/*.mp4`；竖版 1188x2112@30，镜间 xfade 0.4s、章间 0.5s）')
A('- 旧口播文本对照：`shotlist_ch1_vo_v4.json`（ch1）、`script_v4_ch2-6.md` 镜头表（ch2–6）')
A('')
A('## 2. 新 63 镜 ↔ 旧时间轴对应\n')
A('- 63 个镜号与 `inventory.json` 一一对应（ch1 17 / ch2 10 / ch3 9 / ch4 9 / ch5 9 / ch6 9），无缺失、无多出；每镜题材与旧口播段落一致（ch1-c01…c09b 新提示词口播逐字相同，其余为概述，主题一致）。')
A('- 时长：每镜取旧 `out_dur`，按 30fps 取整帧（`frames = round(d·30)`，偏差 ≤ 1/60 s）；63 镜合计 %.1f s（= 旧 shot 时长和 1421.3 s，含 xfade 重叠；旧成片 1397.0 s）。' % sum(x['duration_s'] for x in p))
A('- 不一致（未强行对齐，仅标出）：')
A('  1. 画幅：旧时间轴是竖版 1188x2112；本批次按新静帧输出横版 1920x1080@30。拼接时需另定画幅/裁切方案（不在本阶段）。')
A('  2. 旧时长含 0.4/0.5 s 转场重叠，本批次每镜按旧 shot 时长完整渲染，拼接时同样的 xfade 才能对上原口播。')
A('  3. 旧 ch2–6 的 12 个 select_v1 LTX 循环镜（ch2-c06, ch2-c09, ch3-c08, ch4-c06, ch4-c08, ch5-c02, ch5-c05, ch5-c06, ch6-c02, ch6-c03, ch6-c05, ch6-c07）是旧画面；本批次重新按新静帧选 I2V，仅 ch2-c09、ch5-c06 两镜与旧 I2V 重合。')
A('  4. `edit/landscape_full_v5/v6`（后期横版剪辑）存在，但任务指定旧确认时间轴为 draft_dof_vo_v4，未采用，仅记录。')
A('')
A('## 3. 方法与规则\n')
A('- 默认：静帧 + 推/拉/平移（`shared/camera-motion/camera_motion.py`，affine 后端，CPU，ramped_linear 缓入缓出）。幅度按 MOTION_GUIDELINES（9s 推 ≈13–16%、平移 ≈6–7%）随时长缩放：推拉 zoom = clamp(1.04+0.012·d, 1.05, 1.18)，源图宽 < 1500 时上限 1.12；平移 = clamp(3%+0.4%·d, 3.5%, 9%) 画宽；< 2.5 s 的镜头 zoom 1.04。')
A('- I2V：%d / 63 镜（%.0f%%），只选“确有自然内部运动（云、雾、浪、极光、火、雪、熔岩辉光）且画面细节少、无人物/精密结构”的镜头。' % (len(i2v), 100 * len(i2v) / 63))
A('- 引擎：LTX 2.3 distilled（ManualSigmas，portable ComfyUI 8191，`--disable-pinned-memory`、`--disable-auto-launch`），1280x704、121 帧@24fps、seed 42。依据 PRODUCTION-MOTION-ROUTING：这些镜头属“特殊物理/自然现象”，且本集旧生产 I2V（select_v1）即 LTX，管线已验证（run_i2v_cinematic_test01）；Wan 2.2 路由是人物微动（呼吸/发丝），MiniMax H3 是人物关键动作，均不对应。')
A('- I2V 后处理：裁 16:9 1248x702 → RealBasicVSR x4（`shared/video-restoration/run_vsr_streaming.py`）→ 1920x1080；121 帧以 30fps 1:1 播放，按旧时长用乒乓（均匀运动）或 18 帧交叉淡化循环（有方向的运动）延展，并叠加 ≤6% 的轻推近。不做补帧（补帧留到终审后）。')
A('- I2V 质检：抽帧条 + 时域指标，崩坏/闪烁/主体变形 → 退回同参数推拉（affine 渲染作为每镜兜底，63 镜全渲）。')
A('- RealESRGAN x4：15 个候选静帧（SELECTED.md realesrgan=是）超分后重渲推拉；如队列未放行则保留原图推拉并标注。')
A('- 伪文字处理：10 镜轻模糊（`scripts/clean_regions.json` → `inputs_clean/`）；其中 ch3-c04、ch6-c02、ch6-c03、ch6-c09 罗盘外圈仍可辨伪字，改用扩大罗盘带的 v2（`clean_regions_v2.json` → `inputs_clean_v2/`），v1 文件保留。未加任何箭头/文字/地图标注层（待老大定）。ch6-c02 的圣保罗穹顶时代错位不是文字，未处理。')
A('- GPU：本地 GPU 任务全部走 `shared/gpu-queue/requests/`（esrgan-stills / i2v-ltx / vsr-i2v），granted 后才运行；推拉渲染只用 CPU。')
A('')
A('## 4. 规则冲突（以规则文件为准）\n')
A('1. visual-motion.md「不预设图生视频比例」 vs 任务「2–3 成」：按需选择，结果 %d/63 ≈ %.0f%%，略低于 2 成，未为凑比例加镜。' % (len(i2v), 100 * len(i2v) / 63))
A('2. PRODUCTION-MOTION-ROUTING：微动默认 Wan 2.2，但本集 I2V 镜全是自然现象（无人物），按“特殊物理/旧生产 LTX 镜”路由选 LTX 2.3。')
A('3. video-workflow §3 第 7 条：画质增强（超分/VSR）前需提醒；本次由上级任务明确要求，照做并在此记录。')
A('4. gpu-queue README：提交方须通知管理会话；本执行环境无聊天工具，无法通知，只能把请求 ID 与路径上报。')
A('5. 旧时间轴为竖版，本批次横版（见 §2）。')
A('')
A('## 5. 逐镜计划\n')
A('| 镜头 | 方法 | 运动/幅度 | 旧时长 s | 帧@30 | 输入图 | 清理 | ESRGAN候选 | 理由 |')
A('|---|---|---|---|---|---|---|---|---|')
for x in p:
    m = 'I2V·LTX2.3' if x['method'] == 'i2v' else '推拉(affine)'
    mv = MV[x['motion']] + ' ' + x['affine_magnitude'].replace('zoom ', '').replace(' of frame width', '')
    inp = rel(x.get('i2v_input') or x['affine_input'])
    cl = 'v2' if x['cleaned_input'] and 'inputs_clean_v2' in x['cleaned_input'] else ('v1' if x['cleaned_input'] else '')
    A('| %s | %s | %s | %.3f | %d | `%s` | %s | %s | %s |' % (x['shot'], m, mv, x['old_duration_s'], x['frames_30fps'], inp, cl, '是' if x['realesrgan_candidate'] else '', x['reason'].replace('|', '/')))
A('')
A('## 6. I2V 镜头明细（LTX 2.3）\n')
for x in i2v:
    A('### %s（%.3f s，%s）' % (x['shot'], x['old_duration_s'], {'pingpong': '乒乓循环', 'xfade': '交叉淡化循环'}[x['loop_mode']]))
    A('- 输入：`%s`' % rel(x['i2v_input']))
    A('- 理由：%s' % x['reason'])
    A('- 提示词：%s' % x['i2v_prompt'])
    A('- 兜底：同参数推拉 %s %s' % (MV[x['motion']], x['affine_magnitude']))
    A('')
A('统一负面提示词：%s\n' % i2v[0]['i2v_negative'])
open('docs/MOTION_PLAN.md', 'w', encoding='utf-8').write('\n'.join(L) + '\n')
print(len(L))
