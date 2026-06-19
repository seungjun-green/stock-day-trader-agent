"""Validate pre/post pipeline outputs."""
from __future__ import annotations

import json
import re
from pathlib import Path

PICKS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-picks(?:-([^.]+))?\.json$")


def validate_pre(market_dir: Path, session: str) -> tuple[bool, list[str]]:
    """Check that pre-pipeline produced at least one valid picks JSON."""
    errors: list[str] = []
    day_dir = market_dir / "data" / session
    if not day_dir.is_dir():
        return False, [f"Missing data folder: {day_dir}"]

    picks_files = [
        p for p in day_dir.iterdir()
        if p.is_file() and PICKS_RE.match(p.name) and p.name.startswith(session)
    ]
    if not picks_files:
        return False, [f"No picks JSON in {day_dir}"]

    ok_any = False
    for pf in picks_files:
        try:
            data = json.loads(pf.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            errors.append(f"{pf.name}: invalid JSON — {e}")
            continue
        for track_key in ("track_a_large_mega", "track_b_mid"):
            track = data.get(track_key) or {}
            picks = track.get("final_picks") or []
            if not picks:
                errors.append(f"{pf.name}: {track_key} has no final_picks")
                continue
            ok_any = True
    return ok_any, errors


def validate_post(market_dir: Path, session: str) -> tuple[bool, list[str]]:
    """Check post-pipeline outputs: market_data JSON + summary."""
    errors: list[str] = []
    day_dir = market_dir / "data" / session
    md = day_dir / f"market_data_{session}.json"
    summary = day_dir / f"{session}-summary.txt"

    if not md.is_file():
        errors.append(f"Missing {md.name}")
    else:
        try:
            data = json.loads(md.read_text(encoding="utf-8"))
            combos = data.get("combos") or []
            if not combos:
                errors.append("market_data.json has empty combos")
        except json.JSONDecodeError as e:
            errors.append(f"market_data.json invalid JSON — {e}")

    if not summary.is_file():
        errors.append(f"Missing {summary.name}")
    elif summary.stat().st_size < 100:
        errors.append(f"{summary.name} looks too short")

    return len(errors) == 0, errors
