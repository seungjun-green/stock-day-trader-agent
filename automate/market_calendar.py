"""Trading calendar helpers — session dates and market-open checks."""
from __future__ import annotations

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
ET = ZoneInfo("America/New_York")

_CALENDARS: dict | None = None


def _get_calendars():
    global _CALENDARS
    if _CALENDARS is not None:
        return _CALENDARS
    try:
        import pandas_market_calendars as mcal
    except ImportError:
        _CALENDARS = {}
        return _CALENDARS
    _CALENDARS = {
        "XKRX": mcal.get_calendar("XKRX"),
        "NYSE": mcal.get_calendar("NYSE"),
    }
    return _CALENDARS


def is_trading_day(calendar_name: str, session: date) -> bool:
    """Return True if `session` is a regular trading day on the given exchange."""
    if session.weekday() >= 5:
        return False
    cals = _get_calendars()
    cal = cals.get(calendar_name)
    if cal is None:
        # Fallback: weekdays only (no holiday data without pandas_market_calendars).
        return True
    sched = cal.schedule(start_date=session, end_date=session)
    return not sched.empty


def korean_session_date(now: datetime | None = None) -> date:
    """Korean session folder date = today's calendar date in KST."""
    now = now or datetime.now(KST)
    if now.tzinfo is None:
        now = now.replace(tzinfo=KST)
    return now.astimezone(KST).date()


def us_session_date(phase: str, now: datetime | None = None) -> date:
    """
    US data folder date in ET terms.

    - pre (22:00 KST): same US trading day about to open (~09:00 ET).
    - post (07:00 KST): previous US session that just closed (~18:00 ET prior day).
    """
    now = now or datetime.now(KST)
    if now.tzinfo is None:
        now = now.replace(tzinfo=KST)
    et_now = now.astimezone(ET)
    if phase == "pre":
        return et_now.date()
    # post: at 07:00 KST the US session that closed maps to ET calendar date at 18:00 ET
    # (still the previous US trading day relative to KST morning calendar in edge cases).
    return et_now.date()


def session_date(market_key: str, phase: str, now: datetime | None = None) -> date:
    if market_key == "korean":
        return korean_session_date(now)
    if market_key == "us":
        return us_session_date(phase, now)
    raise ValueError(f"Unknown market: {market_key}")


def parse_hhmm(s: str) -> time:
    h, m = s.split(":")
    return time(int(h), int(m))


def trigger_due(trigger_time: time, now: datetime, grace_minutes: int = 120) -> bool:
    """
    True if local time is at or after trigger_time, within grace window.
    Allows catching up if the scheduler was down (e.g. laptop slept).
    """
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    t = now.timetz().replace(tzinfo=None)
    if t < trigger_time:
        return False
    # Within grace window after trigger (default 2h)
    trigger_dt = datetime.combine(now.date(), trigger_time, tzinfo=now.tzinfo)
    elapsed_min = (now - trigger_dt).total_seconds() / 60
    return 0 <= elapsed_min <= grace_minutes
