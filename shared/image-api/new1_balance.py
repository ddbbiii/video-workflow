# -*- coding: utf-8 -*-
"""NEW1 (mxwell) 余额监视：只读，不产生调用费用。

站点只开放“已用金额”（/v1/dashboard/billing/usage），不开放用户余额；
因此剩余额度 = 你充值的金额 − 已用。充值金额用 --topup 传入（或环境变量 NEW1_TOPUP）。

退出码：0 充足；2 接近耗尽（≤10 次调用）；3 已耗尽（调用会 403）。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
import winreg
from pathlib import Path

BASE = "https://api.mxwell.ai"
UA = "OpenAI/Python 1.60.0"
PRICE_YUAN = 0.02
WARN_CALLS = 10


def key() -> str:
    value = os.environ.get("IMAGE_API_KEY_MX")
    if value:
        return value
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as handle:
        return winreg.QueryValueEx(handle, "IMAGE_API_KEY_MX")[0]


def usage_usd() -> float:
    request = urllib.request.Request(
        f"{BASE}/v1/dashboard/billing/usage",
        headers={"Authorization": f"Bearer {key()}", "User-Agent": UA},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return float(json.loads(response.read().decode("utf-8")).get("total_usage", 0)) / 100.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--topup", type=float, default=float(os.environ.get("NEW1_TOPUP", "0")),
                        help="充值金额（元，按站点 1:1 口径）")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    spent = usage_usd()
    info = {"channel": "new1", "price_per_call_yuan": PRICE_YUAN,
            "spent_yuan": round(spent, 2), "calls_used": round(spent / PRICE_YUAN)}
    if args.topup > 0:
        remaining = args.topup - spent
        calls_left = remaining / PRICE_YUAN
        info.update({"topup_yuan": args.topup, "remaining_yuan": round(remaining, 2),
                     "calls_left": round(calls_left)})
        if remaining <= 0:
            code = 3
        elif calls_left <= WARN_CALLS:
            code = 2
        else:
            code = 0
    else:
        info["note"] = "未提供 --topup，只能报已用；耗尽只能靠 403 insufficient_user_quota 发现"
        code = 0

    if args.json:
        print(json.dumps(info, ensure_ascii=False))
    else:
        print(f"NEW1 已用 {info['spent_yuan']:.2f} 元（约 {info['calls_used']} 次）", end="")
        if "remaining_yuan" in info:
            print(f"；剩余 {info['remaining_yuan']:.2f} 元（约 {info['calls_left']} 次）", end="")
        print()
        if code == 3:
            print("已耗尽：调用会 403 insufficient_user_quota，应立即停止并改用备用通道")
        elif code == 2:
            print(f"接近耗尽（≤{WARN_CALLS} 次）：建议本批结束就停，等用户决定")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
