"""Write this batch's GPU queue requests (status queued). Never starts GPU work. Does not touch other requests."""
import json, time, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; RUN = Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\video\clips')  # 2026-10-08 迁移：原批次 20261007-v3-motion-b01 根目录，现为单集 video\clips
ROOT = Path(r'E:\program\1project\video')
Q = ROOT / 'shared/gpu-queue/requests'
PY311 = r'E:\program\language\python\Python-3.11.0\python.exe'
PORT = str(ROOT / 'shared/runtime/comfy/installs/portable/python_embeded/python.exe')
now = time.strftime('%Y-%m-%dT%H:%M:%S+08:00')
AUTH = '老大 2026-10-07 明确本集跳过 E/G 关、自动做到成片（本集特例，见 P\\PROJECT_STATE.md）；动态阶段 I2V、15 镜 RealESRGAN、I2V 成片 VSR 由所属会话按老大指令下达，本轮不拼接。'
OWNER = '助眠线路 b-geomagnetic-reversal 动态阶段执行助手（经父会话下达；聊天 ID 由父会话补充/转达）'
base = dict(owner_thread=OWNER, line='zhumian-b-geomagnetic-reversal', submitted_at=now, priority=None, status='queued', working_directory=str(RUN),
            output_directory=None, dependencies=[], authorization=AUTH, pid=None, log_path=None)
reqs = [
 dict(id='zhumian-geomag-v3-esrgan-stills-20261007', task='RealESRGAN_x4plus 静帧超分，仅 15 张已登记候选（四格裁片约 1020x572 -> x4）；spandrel fp16 分块，无 ComfyUI。输出到批次 esrgan\\，原图不动。',
      command_or_workflow_path=f'{PY311} {HERE}\\gpu_job.py zhumian-geomag-v3-esrgan-stills-20261007 {RUN}\\logs\\esrgan.log {PORT} {HERE}\\esrgan_stills.py',
      output_directory=str(Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\image\stills') / 'esrgan_x4'), estimated_minutes=10, estimated_vram_mb=5000,
      dependencies=['shared GPU lock (shared/work/cache/gpu.lock; legacy guard checked)', 'RealESRGAN_x4plus.pth in shared/runtime/comfy/models/models/upscale_models'],
      shots=['ch1-c01','ch1-c03','ch1-c06b','ch1-c07','ch1-c11','ch1-c15','ch2-c03','ch2-c05','ch2-c06','ch2-c08','ch3-c06','ch4-c02','ch5-c01','ch6-c02','ch6-c03']),
 dict(id='zhumian-geomag-v3-i2v-ltx-20261007', task='LTX-2.3 distilled 图生视频 12 镜（自然环境运动：海浪/雾/云/极光/火/雪/蒸汽），1280x704、121 帧@24fps、seed42，串行；portable ComfyUI 8191（--disable-pinned-memory，脚本自启自停，不开网页）；段间 /free。失败镜回退推拉。',
      command_or_workflow_path=f'{PY311} {HERE}\\gpu_job.py zhumian-geomag-v3-i2v-ltx-20261007 {RUN}\\logs\\i2v.log {PY311} {HERE}\\run_i2v_ltx.py',
      output_directory=str(Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\archive\gen_rebuild\runs\20261007-v3-motion-b01') / 'i2v'), estimated_minutes=90, estimated_vram_mb=15000,
      dependencies=['shared GPU lock', 'port 8191 free', 'LTX-2.3 models in portable ComfyUI', 'ffmpeg'],
      shots=['ch1-c08','ch2-c07','ch2-c09','ch3-c05','ch3-c07','ch3-c09','ch4-c03','ch5-c06','ch5-c07','ch5-c08','ch6-c01','ch6-c08'],
      notes=['不得扩展到其他镜头', '不改 rules/管线代码；脚本只在本批次 scripts\\', '失败保留日志']),
 dict(id='zhumian-geomag-v3-vsr-i2v-20261007', task='RealBasicVSR x4 高清修复：仅对通过抽帧 QA 的 I2V 片段（最多 12 条，16:9 裁切 1248x702 输入），逐镜调用 shared/video-restoration/run_vsr_streaming.py（每镜自取自放共享锁，新 run 目录），任一镜失败即停批。',
      command_or_workflow_path=f'{PY311} {HERE}\\gpu_job.py zhumian-geomag-v3-vsr-i2v-20261007 {RUN}\\logs\\vsr.log {PY311} {HERE}\\run_vsr_batch.py',
      output_directory=str(Path(r'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\archive\gen_rebuild\runs\20261007-v3-motion-b01') / 'vsr'), estimated_minutes=150, estimated_vram_mb=12000,
      dependencies=['zhumian-geomag-v3-i2v-ltx-20261007 completed', '所属会话完成 I2V 抽帧 QA（qa\\i2v_qa.json）', 'shared GPU lock'],
      notes=['VSR 交付版 visual_qa 需人工看联系表后才改 passed', 'QA fail 时回退 Lanczos 基线']),
]
for r in reqs:
    p = Q / f"{r['id']}.json"
    if p.exists(): print('exists, not overwritten:', p); continue
    d = dict(base); d.update(r)
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8'); print('wrote', p)
