# -*- coding: utf-8 -*-
"""渲染前校验 motion_plan.json。

检查每镜：
- 必填 id / duration_s / start_view / end_view，以及 source（或 source_path）；
- 源文件存在，且不是纯黑、纯色占位；
- 推近/拉远/横移幅度不低于默认下限：
  常规推近 9%，拉远 8%，时长 >25 s 的长镜 7%，横移 6%。
静态镜（start_view == end_view）允许，不报错。

用法：
  python shared/camera-motion/validate_plan.py <motion_plan.json>
  python shared/camera-motion/validate_plan.py <motion_plan.json> --allow-below-floor --reason "用户已确认长镜减幅"

退出码 0 = PASS，1 = FAIL。
"""
import argparse
import json
import sys
from pathlib import Path

try:
    from PIL import Image, ImageStat
except Exception:  # pragma: no cover - 环境缺 Pillow 时仍做结构校验
    Image = None
    ImageStat = None

PUSH_FLOOR = 0.09
PULL_FLOOR = 0.08
LONG_PUSH_FLOOR = 0.07
PAN_FLOOR = 0.06
LONG_SHOT_S = 25.0


def image_stats(path: Path):
    """返回 (mean, stddev)；无法读取时返回 (None, None)。"""
    if Image is None:
        return None, None
    try:
        with Image.open(path) as im:
            im = im.convert("L")
            im.thumbnail((256, 256))
            stat = ImageStat.Stat(im)
            return float(stat.mean[0]), float(stat.stddev[0])
    except Exception:
        return None, None


def zoom(view):
    w = float(view[2])
    return 1.0 / w if w > 0 else 0.0


def main() -> int:
    ap = argparse.ArgumentParser(description="校验 motion_plan.json 再渲染")
    ap.add_argument("plan", help="motion_plan.json 路径")
    ap.add_argument("--allow-below-floor", action="store_true",
                    help="低于幅度下限时只告警；必须同时给 --reason")
    ap.add_argument("--reason", default="", help="低于下限的批准理由")
    args = ap.parse_args()

    plan_path = Path(args.plan)
    if not plan_path.exists():
        print(f"FAIL: 找不到 plan：{plan_path}")
        return 1

    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"FAIL: plan 不是合法 JSON：{e!r}")
        return 1

    shots = plan.get("shots")
    if not isinstance(shots, list) or not shots:
        print("FAIL: plan 里没有 shots")
        return 1

    errors = []
    warnings = []

    for idx, s in enumerate(shots):
        sid = str(s.get("id") or f"#{idx}")

        for key in ("id", "duration_s", "start_view", "end_view"):
            if key not in s:
                errors.append(f"{sid}: 缺少字段 {key}")
        if "duration_s" not in s or "start_view" not in s or "end_view" not in s:
            continue

        src_val = s.get("source") or s.get("source_path")
        if not src_val:
            errors.append(f"{sid}: 缺少 source / source_path")
            continue
        src = Path(str(src_val))
        if not src.is_absolute():
            src = (plan_path.parent / src).resolve()
        if not src.exists():
            errors.append(f"{sid}: 源文件不存在：{src}")
            continue
        if not src.is_file():
            errors.append(f"{sid}: source 不是文件：{src}")
            continue

        mean, std = image_stats(src)
        if mean is not None and std is not None:
            if mean < 5.0 and std < 3.0:
                errors.append(f"{sid}: 源图接近纯黑（mean={mean:.1f}, std={std:.1f}）")
            elif std < 1.0:
                errors.append(f"{sid}: 源图接近纯色（std={std:.1f}）")

        try:
            dur = float(s["duration_s"])
            sv = [float(x) for x in s["start_view"]]
            ev = [float(x) for x in s["end_view"]]
            if len(sv) != 4 or len(ev) != 4:
                raise ValueError("view 必须是 [x, y, w, h]")
        except Exception as e:
            errors.append(f"{sid}: duration/view 不合法（{e}）")
            continue
        if dur <= 0:
            errors.append(f"{sid}: duration_s 必须 >0")
            continue

        z0, z1 = zoom(sv), zoom(ev)
        if z0 <= 0 or z1 <= 0:
            errors.append(f"{sid}: view 宽度必须 >0")
            continue
        dx = abs(ev[0] - sv[0])

        if abs(z1 - z0) > 1e-9:
            if z1 > z0:
                amp = z1 / z0 - 1.0
                kind = "推近"
                floor = LONG_PUSH_FLOOR if dur > LONG_SHOT_S else PUSH_FLOOR
            else:
                amp = 1.0 - z1 / z0
                kind = "拉远"
                floor = LONG_PUSH_FLOOR if dur > LONG_SHOT_S else PULL_FLOOR
        elif dx > 1e-9:
            amp = dx
            kind = "横移"
            floor = PAN_FLOOR
        else:
            continue  # 静态镜允许

        if amp + 1e-9 < floor:
            msg = (f"{sid}: {kind}幅度 {amp * 100:.1f}% < 下限 {floor * 100:.0f}%"
                   f"（时长 {dur:.1f}s）")
            if args.allow_below_floor and args.reason:
                warnings.append(msg + f" [已批准：{args.reason}]")
            else:
                errors.append(msg)

    for w in warnings:
        print("WARN:", w)
    for e in errors:
        print("FAIL:", e)

    if errors:
        print(f"FAIL: {len(errors)} 项错误 / {len(shots)} 镜")
        return 1

    print(f"PASS: {len(shots)} 镜")
    return 0


if __name__ == "__main__":
    sys.exit(main())
