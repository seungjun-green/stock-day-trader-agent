"""Run pre/post pipeline scripts with retries."""
from __future__ import annotations

import subprocess
import sys
from datetime import date
from pathlib import Path

from automate.validate import validate_post, validate_pre

REPO_ROOT = Path(__file__).resolve().parent.parent


def run_script(market_dir: Path, script: str, session: str, extra_args: list[str] | None = None) -> tuple[int, str]:
    cmd = [sys.executable, script, "--date", session.isoformat()]
    if extra_args:
        cmd.extend(extra_args)
    proc = subprocess.run(
        cmd,
        cwd=market_dir,
        capture_output=True,
        text=True,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out


def run_pre(market_key: str, market_dir: Path, session: date, max_retries: int = 3) -> tuple[bool, str]:
    last_out = ""
    for attempt in range(1, max_retries + 1):
        print(f"[{market_key}] pre-pipeline attempt {attempt}/{max_retries} session={session}")
        code, out = run_script(market_dir, "pre-pipeline.py", session)
        last_out = out
        ok, errors = validate_pre(market_dir, session.isoformat())
        if code == 0 and ok:
            return True, out
        print(f"[{market_key}] pre validation failed: {errors}")
    return False, last_out


def run_post(market_key: str, market_dir: Path, session: date, max_retries: int = 3) -> tuple[bool, str]:
    last_out = ""
    for attempt in range(1, max_retries + 1):
        print(f"[{market_key}] post-pipeline attempt {attempt}/{max_retries} session={session}")
        code, out = run_script(market_dir, "post-pipeline.py", session)
        last_out = out
        ok, errors = validate_post(market_dir, session.isoformat())
        if code == 0 and ok:
            return True, out
        print(f"[{market_key}] post validation failed: {errors}")
    return False, last_out
