# -*- coding: utf-8 -*-
"""Controlled simulation specs for newton-to-chaos.

All sims: Newtonian gravity (or stated ODE), dimensionless units G=1 unless noted,
fixed-step integrator (velocity Verlet for gravity systems, RK4 for Lorenz),
deterministic starfield seed. Renderer writes the executed initial conditions,
step size, step count, and units into each run manifest. Aesthetic: deep
teal-blue space, amber/cyan glowing bodies, fading light-ribbon trails; no
labels, no axes, no text.
"""

SIMS = {
 # ---- two-body ----
 "two_body_ellipse": dict(system="gravity2", bodies=2, masses=[1.0, 0.35],
   intent="中等质量比双星，近椭圆轨道(e约0.2)，两条光带轨迹清晰整齐", duration_s=20),
 "two_body_ellipse_wide": dict(system="gravity2", bodies=2, masses=[1.0, 0.35],
   intent="同上更宽机位更长时长，完整呈现椭圆闭环", duration_s=26),
 "two_body_barycenter": dict(system="gravity2", bodies=2, masses=[1.0, 0.12],
   intent="质量悬殊，两天体都绕共同质心运动：小天体大椭圆、大天体小椭圆，质心处一个不发光的十字微光标记", duration_s=22),
 "two_body_eccentric": dict(system="gravity2", bodies=2, masses=[1.0, 0.6],
   intent="偏心轨道(e约0.6)，近日端明显加速，远日端缓慢", duration_s=24),
 # ---- three-body general ----
 "three_body_slow_drift": dict(system="gravity3", bodies=3, masses=[1.0, 0.9, 0.8],
   intent="三颗近等质量天体缓慢漂移互绕，短尾迹，位置持续改变", duration_s=18),
 "three_body_perturb": dict(system="gravity3", bodies=3, masses=[1.0, 0.9, 0.35],
   intent="双星+第三体，扰动沿相互引力传递，一颗被拉偏后其余依次改变", duration_s=20),
 "three_body_numeric": dict(system="gravity3", bodies=3, masses=[1.0, 0.8, 0.6],
   intent="三体轨迹按等长时间步分段点亮，步进感清晰，体现一步一步推进", duration_s=22, step_visual=True),
 "three_body_numeric_fine": dict(system="gravity3", bodies=3, masses=[1.0, 0.8, 0.6],
   intent="同一初始条件更细步长重走，步进感减弱趋于连续", duration_s=22, step_visual_fine=True),
 "three_body_figure8": dict(system="gravity3", bodies=3, masses=[1.0, 1.0, 1.0],
   intent="三体8字周期轨道(Chenciner-Montgomery标准初值)，三颗等质量天体沿同一8字光带首尾相接运行", duration_s=26,
   standard_ic="figure8_chenciner_montgomery"),
 "three_body_scattering_far": dict(system="gravity3", bodies=3, masses=[1.0, 0.9, 0.30],
   intent="紧密双星+远处第三体缓慢接近，影响尚温和", duration_s=20),
 "three_body_scattering_close": dict(system="gravity3", bodies=3, masses=[1.0, 0.9, 0.30],
   intent="近距离相遇：作用变强，能量在三者间重新分配，最终一体被抛出", duration_s=26),
 "three_body_scattering_after": dict(system="gravity3", bodies=3, masses=[1.0, 0.9, 0.30],
   intent="相遇之后：更紧的双星与远去的逃逸体，长尾迹", duration_s=22),
 "three_body_encounter_variants": dict(system="gravity3", bodies=3, masses=[1.0, 0.9, 0.30],
   intent="同一双星，第三体以略不同相位/速度接近，两条演化(青与琥珀)叠加对比，走向明显不同", duration_s=26, dual_variant=True),
 # ---- divergence ----
 "divergence_intro": dict(system="gravity3", bodies=3, masses=[1.0, 0.8, 0.5],
   intent="两次计算的开始：两组几乎重合的轨迹(青/琥珀)从同一起点出发", duration_s=16, dual_variant=True),
 "divergence_start": dict(system="gravity3", bodies=3, masses=[1.0, 0.8, 0.5],
   intent="起点特写：两组初值只差一丝，两颗光点几乎叠在一起", duration_s=18, dual_variant=True, closeup=True),
 "divergence_grow": dict(system="gravity3", bodies=3, masses=[1.0, 0.8, 0.5],
   intent="中段：两条轨迹从重合到分开，距离迅速增长", duration_s=22, dual_variant=True),
 "divergence_outcome": dict(system="gravity3", bodies=3, masses=[1.0, 0.8, 0.5],
   intent="结局：一组抛向另一方向，留下的双星成员也不同", duration_s=24, dual_variant=True),
 "ensemble_fan": dict(system="gravity3_ensemble", n=24, masses=[1.0, 0.8, 0.5],
   intent="从一小片区域出发的24条细线轨迹，起初挤在一起后逐渐铺开", duration_s=22),
 "ensemble_fan_bounded": dict(system="gravity3_ensemble", n=24, masses=[1.0, 0.8, 0.5],
   intent="更长时限：细线群铺开但受系统尺度约束，增长趋于饱和", duration_s=28),
 # ---- double pendulum / Lorenz ----
 "double_pendulum_chaotic": dict(system="double_pendulum",
   intent="双摆两次极接近释放(相差0.001rad)，双尾迹(青/琥珀)逐渐走出不同路径", duration_s=24, dual=True),
 "double_pendulum_regular": dict(system="double_pendulum",
   intent="低能量小幅摆动，单尾迹近乎周期重复", duration_s=20, low_energy=True),
 "lorenz_attractor": dict(system="lorenz", sigma=10.0, rho=28.0, beta=8.0/3.0,
   intent="洛伦兹吸引子：两条极近初值的轨线绘出蝴蝶形双叶光轨，缓慢演化后分离到两叶", duration_s=28, dual=True),
 # ---- fitting ----
 "fit_scatter": dict(system="scatterfit",
   intent="萤火般光点沿隐藏趋势散布，偏高偏低含噪声，趋势线不显示", duration_s=16, mode="scatter"),
 "fit_underfit": dict(system="scatterfit",
   intent="点群+一条笔直光带穿过，抓不住弯曲趋势", duration_s=16, mode="underfit"),
 "fit_good": dict(system="scatterfit",
   intent="点群+适度弯曲光带贴趋势而行", duration_s=16, mode="good"),
 "fit_overfit": dict(system="scatterfit",
   intent="点群+高自由度光带在点间绕行", duration_s=18, mode="overfit"),
 "fit_overfit_perfect": dict(system="scatterfit",
   intent="同上更近机位：每个旧点都在线上，纸面零错误", duration_s=16, mode="overfit", closeup=True),
 "fit_overfit_newpoint": dict(system="scatterfit",
   intent="新增一粒光点落在带外，狂舞光带并未经过它", duration_s=18, mode="overfit_newpoint"),
 "two_problems_split": dict(system="composite",
   intent="同一深空场景两个区域：左为点群+偏学光带(过拟合)，右为邻近轨迹分离(混沌)，以纵深自然分隔不做分栏", duration_s=22),
 # ---- ch07/ch08 ----
 "iterated_drift": dict(system="iterated_prediction",
   intent="真实轨迹(细青)与模型自回归链式预测(琥珀)并走，链式足迹逐步偏离真实轨迹", duration_s=22),
 "ensemble_orbits": dict(system="gravity3_ensemble", n=18, masses=[1.0, 0.8, 0.5],
   intent="18条从略异初值出发的可能轨道同时展开", duration_s=24),
 "ensemble_tight_spread": dict(system="gravity3_ensemble", n=14, masses=[1.0, 0.8, 0.5],
   intent="两簇对比：一簇长时间聚拢，一簇很快分散", duration_s=26, two_clusters=True),
 "ensemble_clouds": dict(system="particle_weather", n_members=9,
   intent="9组成员的云团粒子演化俯瞰：多数成员把雨带(暗琥珀粒子带)聚向同区，少数分歧", duration_s=24),
 "pendulum_bounded": dict(system="double_pendulum",
   intent="钟摆光迹反复扫过中央，细密难辨，但始终限制在一个柔光边界域内", duration_s=22, bounded_region=True),
}

# gravity systems: velocity-Verlet, dt=0.002, dimensionless G=1; masses/ICs written per-run.
# lorenz: RK4 dt=0.005. double pendulum: RK4 on Lagrangian equations, dt=0.001.
# scatterfit: fixed seeded point cloud (seed 7), ribbon = polynomial fits of stated degree.
# particle_weather: deterministic advection of seeded particles with member-dependent perturbation.
