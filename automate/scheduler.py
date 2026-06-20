#!/usr/bin/env python3
"""
Scheduler daemon — runs pre/post pipelines on trading days, then worker agent.

Schedules (Asia/Seoul):
  Korean: pre 08:30, post 16:30
  US:     pre 22:00, post 07:00

Usage:
    python automate/scheduler.py              # run forever (both markets)
    python automate/scheduler.py --once pre   # force pre for due market today
    python automate/scheduler.py --once post
    python automate/scheduler.py --market korean --once pre --date 2026-06-19
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import date, datetime
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from automate.market_calendar import (
    KST,
    is_trading_day,
    parse_hhmm,
    session_date,
    trigger_due,
)
from automate.env_loader import load_dotenv
from automate.pipeline import run_post, run_pre
from automate import state as run_state
from automate.telegram import send_message
from automate.validate import validate_pre

load_dotenv()


def telegram_prefix(market_key: str) -> str:
    return "[KOREA]" if market_key == "korean" else "[US]"


def closed_reason(session: date) -> str:
    weekday = session.strftime("%A")
    if session.weekday() >= 5:
        return weekday
    return "exchange holiday"


def already_sent_closed_notice(market_key: str, session: date) -> bool:
    st = run_state.load(market_key)
    return st.get("last_closed_notice") == session.isoformat()


def mark_closed_notice_sent(market_key: str, session: date) -> None:
    st = run_state.load(market_key)
    st["last_closed_notice"] = session.isoformat()
    run_state.save(market_key, st)


def send_closed_notice_once(market_key: str, label: str, session: date) -> None:
    if already_sent_closed_notice(market_key, session):
        return
    send_message(
        f"{telegram_prefix(market_key)} ⏭️ {label} skipped today — `{session}`\n"
        f"Reason: market closed ({closed_reason(session)})."
    )
    mark_closed_notice_sent(market_key, session)


def load_config() -> dict:
    path = REPO_ROOT / "automate" / "config.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def run_worker_subprocess(market_key: str, session: date) -> int:
    import subprocess
    proc = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "automate" / "worker.py"),
            "--market", market_key,
            "--date", session.isoformat(),
        ],
        cwd=REPO_ROOT,
    )
    return proc.returncode


def process_market(cfg: dict, market_key: str, now: datetime, force_phase: str | None = None, force_date: date | None = None):
    mcfg = cfg["markets"][market_key]
    market_dir = REPO_ROOT / mcfg["market_dir"]
    cal_name = mcfg["calendar"]
    label = mcfg["label"]
    max_retries = cfg.get("max_retries", 3)

    pre_time = parse_hhmm(mcfg["pre_time"])
    post_time = parse_hhmm(mcfg["post_time"])

    phases = []
    if force_phase:
        phases = [force_phase]
    else:
        if trigger_due(pre_time, now):
            phases.append("pre")
        if trigger_due(post_time, now):
            phases.append("post")

    for phase in phases:
        sess = force_date or session_date(market_key, phase, now)
        if not is_trading_day(cal_name, sess):
            print(f"[{market_key}] {phase}: {sess} not a trading day — skip")
            send_closed_notice_once(market_key, label, sess)
            continue
        if run_state.already_ran(market_key, phase, sess) and not force_phase:
            continue

        print(f"[{market_key}] Running {phase}-pipeline for session {sess}")

        if phase == "pre":
            ok, out = run_pre(market_key, market_dir, sess, max_retries)
            if ok:
                run_state.mark_ran(market_key, phase, sess)
                send_message(f"{telegram_prefix(market_key)} ✅ {label} pre-pipeline done — `{sess}`")
            else:
                send_message(f"{telegram_prefix(market_key)} ❌ {label} pre-pipeline FAILED — `{sess}`\n```\n{out[-500:]}\n```")
        else:
            pre_ok, pre_errors = validate_pre(market_dir, sess.isoformat())
            if not pre_ok:
                if not force_phase:
                    run_state.mark_ran(market_key, phase, sess)
                details = "; ".join(pre_errors[:3]) or "pre-pipeline outputs missing"
                send_message(
                    f"{telegram_prefix(market_key)} ⏭️ {label} post-pipeline skipped — `{sess}`\n"
                    f"Reason: pre-pipeline was not run or output is incomplete.\n"
                    f"Details: {details}"
                )
                continue

            ok, out = run_post(market_key, market_dir, sess, max_retries)
            if ok:
                run_state.mark_ran(market_key, phase, sess)
                send_message(f"{telegram_prefix(market_key)} ✅ {label} post-pipeline done — `{sess}`")
                # Worker agent after successful post
                wcode = run_worker_subprocess(market_key, sess)
                if wcode != 0:
                    send_message(f"{telegram_prefix(market_key)} ⚠️ {label} worker agent failed — `{sess}` (exit {wcode})")
            else:
                send_message(f"{telegram_prefix(market_key)} ❌ {label} post-pipeline FAILED — `{sess}`\n```\n{out[-500:]}\n```")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", choices=["korean", "us"], help="Limit to one market")
    parser.add_argument("--once", choices=["pre", "post"], help="Run one phase immediately")
    parser.add_argument("--date", help="Override session date YYYY-MM-DD (with --once)")
    args = parser.parse_args()

    cfg = load_config()
    markets = [args.market] if args.market else list(cfg["markets"].keys())
    force_date = date.fromisoformat(args.date) if args.date else None

    if args.once:
        now = datetime.now(KST)
        for mk in markets:
            process_market(cfg, mk, now, force_phase=args.once, force_date=force_date)
        return

    poll = cfg.get("poll_interval_seconds", 60)
    print(f"Scheduler started — polling every {poll}s (timezone Asia/Seoul)")
    print(f"Markets: {', '.join(markets)}")
    send_message(
        "[BOT] 🤖 Stock day-trade automation started\n\n"
        f"Markets: {', '.join(markets)}\n"
        f"Poll interval: {poll}s\n"
        "Timezone: Asia/Seoul"
    )

    while True:
        now = datetime.now(KST)
        for mk in markets:
            try:
                process_market(cfg, mk, now)
            except Exception as e:
                print(f"[{mk}] error: {e}")
                send_message(f"{telegram_prefix(mk)} ⚠️ Scheduler error ({mk}): {e}")
        time.sleep(poll)


if __name__ == "__main__":
    main()
