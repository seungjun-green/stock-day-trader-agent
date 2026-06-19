#!/usr/bin/env python3
"""Run automation smoke tests."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def run(name: str, args: list[str], required: bool = True) -> bool:
    print(f"\n== {name} ==")
    proc = subprocess.run(
        [sys.executable, *args],
        cwd=REPO_ROOT,
        text=True,
    )
    if proc.returncode == 0:
        print(f"{name}=ok")
        return True
    print(f"{name}=failed exit={proc.returncode}")
    if required:
        raise SystemExit(proc.returncode)
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--telegram", action="store_true", help="Send a real Telegram test message")
    parser.add_argument("--date", default="2026-06-19", help="Date for report link test")
    parser.add_argument("--market", choices=["korean", "us"], default="korean")
    args = parser.parse_args()

    run("worker_smoke", ["test/worker_smoke_test.py"])
    run("worker_py_compile", ["-m", "py_compile", "automate/worker.py"])
    run("report_link", ["test/report_link_test.py", "--market", args.market, "--date", args.date], required=False)

    if args.telegram:
        run("telegram", ["test/send_telegram_test.py"])
    else:
        print("\n== telegram ==\nskipped (use --telegram to send a real message)")

    print("\nAll required smoke tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
