"""Persistent per-market run state (avoid double-runs on same session date)."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

STATE_DIR = Path(__file__).resolve().parent / "state"


def _path(market_key: str) -> Path:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    return STATE_DIR / f"{market_key}.json"


def load(market_key: str) -> dict:
    p = _path(market_key)
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save(market_key: str, data: dict) -> None:
    _path(market_key).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def already_ran(market_key: str, phase: str, session: date) -> bool:
    st = load(market_key)
    return st.get(f"last_{phase}") == session.isoformat()


def mark_ran(market_key: str, phase: str, session: date) -> None:
    st = load(market_key)
    st[f"last_{phase}"] = session.isoformat()
    save(market_key, st)
