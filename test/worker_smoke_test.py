#!/usr/bin/env python3
"""Dry-run worker output behavior without calling Anthropic, Telegram, or git."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from automate import state as run_state
from automate.worker import (
    apply_observer_outputs,
    apply_outputs,
    mark_observer_ran,
    observer_due,
    report_path,
)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    with TemporaryDirectory() as tmp:
        market_dir = Path(tmp) / "korean"
        (market_dir / "data" / "2026-06-19").mkdir(parents=True)
        (market_dir / "prompts").mkdir()
        (market_dir / "JOURNEY.md").write_text("# Journey\n", encoding="utf-8")

        payload = {
            "improvement_md": "# Improvement\n\nDry-run improvement.",
            "journey_append_md": "## 2026-06-19\n\nDry-run journey append.",
            "strategy_md": "# Strategy\n\nv3-v3-v3: ACTIVE",
            "report_md": "# Daily Report\n\nFull markdown report body.",
            "telegram_summary": "v3-v3-v3:\nTrack A: +1.00%\nTrack B: -0.50%",
            "change_log": "Created brief_agent_v4.txt in dry-run.",
            "file_updates": [
                {
                    "path": "prompts/brief_agent_v4.txt",
                    "reason": "dry-run new prompt version",
                    "content": "Brief agent v4 dry-run prompt.",
                },
                {
                    "path": "../bad.txt",
                    "reason": "should be rejected",
                    "content": "bad",
                },
            ],
        }

        result = apply_outputs(market_dir, "2026-06-19", payload)

        assert_true((market_dir / "data" / "2026-06-19" / "2026-06-19-improvement.md").is_file(), "missing improvement")
        assert_true((market_dir / "JOURNEY.md").read_text(encoding="utf-8").count("2026-06-19") == 1, "journey append failed")
        assert_true((market_dir / "STRATEGY.md").is_file(), "missing strategy")
        assert_true(report_path(market_dir, "2026-06-19").is_file(), "missing markdown report")
        assert_true((market_dir / "prompts" / "brief_agent_v4.txt").is_file(), "new prompt was not created")
        assert_true(result["status"] == "applied", f"unexpected update status: {result}")
        assert_true(len(result["applied"]) == 1, f"unexpected applied count: {result}")
        assert_true(len(result["rejected"]) == 1, f"unexpected rejected count: {result}")

        change_log = market_dir / "reports" / "2026-06-19-worker-changes.json"
        assert_true(change_log.is_file(), "missing worker change log")
        parsed = json.loads(change_log.read_text(encoding="utf-8"))
        assert_true(parsed["status"] == "applied", "change log status mismatch")

        observer_payload = {
            "observer_guidance_md": "# Observer Guidance\n\nKeep notes concise.",
            "observer_report_md": "# Observer Report\n\nNo rabbit hole detected.",
            "telegram_note": "Observer: no rabbit hole detected.",
            "change_log": "Updated observer guidance.",
            "file_updates": [
                {
                    "path": "OBSERVER_GUIDANCE.md",
                    "reason": "dry-run observer guidance",
                    "content": "# Observer Guidance\n\nPrefer evidence over new rules.",
                },
                {
                    "path": "../us/prompts/bad.txt",
                    "reason": "should be rejected",
                    "content": "bad",
                },
            ],
        }
        observer_result = apply_observer_outputs(market_dir, "2026-06-19", observer_payload)
        assert_true((market_dir / "OBSERVER_GUIDANCE.md").is_file(), "missing observer guidance")
        assert_true((market_dir / "reports" / "2026-06-19-observer-report.md").is_file(), "missing observer report")
        assert_true((market_dir / "reports" / "2026-06-19-observer-changes.json").is_file(), "missing observer change log")
        assert_true(observer_result["status"] == "applied", f"unexpected observer status: {observer_result}")
        assert_true(len(observer_result["applied"]) == 1, f"unexpected observer applied count: {observer_result}")
        assert_true(len(observer_result["rejected"]) == 1, f"unexpected observer rejected count: {observer_result}")

    market_key = "worker-smoke-test"
    run_state.save(market_key, {})
    assert_true(observer_due(market_key, "2026-06-19", 7), "observer should run when no prior state")
    mark_observer_ran(market_key, "2026-06-19")
    assert_true(not observer_due(market_key, "2026-06-20", 7), "observer should skip before weekly interval")
    assert_true(observer_due(market_key, "2026-06-26", 7), "observer should run at weekly interval")
    state_path = REPO_ROOT / "automate" / "state" / f"{market_key}.json"
    if state_path.exists():
        state_path.unlink()

    print("worker_smoke=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
