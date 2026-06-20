#!/usr/bin/env python3
"""
Worker agent — post-pipeline review, file updates, Telegram report.

Usage:
    python automate/worker.py --market korean --date 2026-06-18
    python automate/worker.py --market us --date 2026-06-18
"""
from __future__ import annotations

import argparse
import json
import py_compile
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.parse import quote

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from automate.env_loader import load_dotenv
from automate import state as run_state
from automate.telegram import send_message
from automate.validate import validate_post, validate_pre

load_dotenv()

try:
    from anthropic import Anthropic
except ImportError:
    print("Install: pip3 install anthropic")
    sys.exit(1)

WORKER_MODEL = "claude-sonnet-4-6"
OBSERVER_MODEL = "claude-sonnet-4-6"
MAX_POST_RETRIES = 3
EDITABLE_TEXT_LIMIT = 60_000


def telegram_prefix(market_key: str) -> str:
    return "[KOREA]" if market_key == "korean" else "[US]"


def _read(path: Path, limit: int = 120_000) -> str:
    if not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8")
    return text[:limit] if len(text) > limit else text


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("{"):
        return json.loads(text)
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        raise ValueError("No JSON object in worker response")
    return json.loads(m.group(0))


def load_config() -> dict:
    path = REPO_ROOT / "automate" / "config.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def observer_interval_days(cfg: dict) -> int:
    observer_cfg = cfg.get("observer", {}) or {}
    return int(observer_cfg.get("interval_days", 7))


def observer_due(market_key: str, session: str, interval_days: int) -> bool:
    st = run_state.load(market_key)
    last = st.get("last_observer")
    if not last:
        return True
    try:
        elapsed = (date.fromisoformat(session) - date.fromisoformat(last)).days
    except ValueError:
        return True
    return elapsed >= interval_days


def mark_observer_ran(market_key: str, session: str) -> None:
    st = run_state.load(market_key)
    st["last_observer"] = session
    run_state.save(market_key, st)


def gather_context(market_dir: Path, session: str, market_label: str) -> str:
    day = market_dir / "data" / session
    parts = [f"# Worker context — {market_label} — {session}\n"]

    summary = day / f"{session}-summary.txt"
    parts.append(f"## summary.txt\n{_read(summary)}\n")

    md = day / f"market_data_{session}.json"
    parts.append(f"## market_data.json\n{_read(md, 80_000)}\n")

    perf = market_dir / "data" / "variant_performance.csv"
    parts.append(f"## variant_performance.csv\n{_read(perf, 20_000)}\n")

    imp = day / f"{session}-improvement.md"
    parts.append(f"## existing improvement.md\n{_read(imp)}\n")

    journey = market_dir / "JOURNEY.md"
    parts.append(f"## JOURNEY.md (tail)\n{_read(journey)[-15_000:]}\n")

    strategy = market_dir / "STRATEGY.md"
    parts.append(f"## STRATEGY.md\n{_read(strategy)}\n")

    guidance = market_dir / "OBSERVER_GUIDANCE.md"
    parts.append(f"## OBSERVER_GUIDANCE.md\n{_read(guidance)}\n")

    # First picks file for reasoning sample
    picks = sorted(day.glob(f"{session}-picks-*.json"))
    if picks:
        parts.append(f"## picks sample ({picks[0].name})\n{_read(picks[0], 30_000)}\n")

    editable_files = _editable_files(market_dir)
    parts.append("## Editable files available for autonomous updates\n")
    parts.append(
        "You may return file_updates for these relative paths only. "
        "Use full replacement content. Edit prompts freely when justified by today's results; "
        "edit Python code only for small, high-confidence rule/filter/simulation changes.\n"
    )
    for rel_path, path in editable_files.items():
        text = _read(path, EDITABLE_TEXT_LIMIT)
        truncated = "\n[TRUNCATED: file is longer than worker context limit]\n" if path.is_file() and len(path.read_text(encoding="utf-8")) > EDITABLE_TEXT_LIMIT else ""
        parts.append(f"### {rel_path}\n{text}{truncated}\n")

    return "\n".join(parts)


def run_worker(market_key: str, market_dir: Path, session: str, market_label: str) -> dict:
    prompt_path = REPO_ROOT / "automate" / "prompts" / "worker_agent.txt"
    system = prompt_path.read_text(encoding="utf-8").format(market_label=market_label)
    user = gather_context(market_dir, session, market_label)

    client = Anthropic()
    response = client.messages.create(
        model=WORKER_MODEL,
        max_tokens=8192,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = ""
    for block in response.content:
        if hasattr(block, "text"):
            text += block.text
    return _extract_json(text)


def _recent_improvement_files(market_dir: Path, limit: int = 5) -> list[Path]:
    data_dir = market_dir / "data"
    if not data_dir.is_dir():
        return []
    files = sorted(data_dir.glob("*/????-??-??-improvement.md"))
    return files[-limit:]


def gather_observer_context(market_dir: Path, session: str, market_label: str) -> str:
    parts = [f"# Observer context — {market_label} — {session}\n"]

    parts.append(f"## JOURNEY.md (tail)\n{_read(market_dir / 'JOURNEY.md')[-20_000:]}\n")
    parts.append(f"## STRATEGY.md\n{_read(market_dir / 'STRATEGY.md')}\n")
    parts.append(f"## OBSERVER_GUIDANCE.md\n{_read(market_dir / 'OBSERVER_GUIDANCE.md')}\n")
    parts.append(f"## variant_performance.csv\n{_read(market_dir / 'data' / 'variant_performance.csv', 30_000)}\n")

    for path in _recent_improvement_files(market_dir):
        parts.append(f"## Recent improvement: {path.relative_to(market_dir)}\n{_read(path, 35_000)}\n")

    today_report = report_path(market_dir, session)
    parts.append(f"## Today's daily report\n{_read(today_report, 40_000)}\n")

    editable_files = _editable_files(market_dir)
    parts.append("## Editable files available for observer updates\n")
    parts.append(
        "You may return file_updates for these relative paths only. "
        "Use full replacement content. Keep changes market-scoped.\n"
    )
    for rel_path, path in editable_files.items():
        text = _read(path, EDITABLE_TEXT_LIMIT)
        truncated = "\n[TRUNCATED: file is longer than observer context limit]\n" if path.is_file() and len(path.read_text(encoding="utf-8")) > EDITABLE_TEXT_LIMIT else ""
        parts.append(f"### {rel_path}\n{text}{truncated}\n")

    return "\n".join(parts)


def run_observer(market_key: str, market_dir: Path, session: str, market_label: str) -> dict:
    prompt_path = REPO_ROOT / "automate" / "prompts" / "observer_agent.txt"
    system = prompt_path.read_text(encoding="utf-8").format(market_label=market_label)
    user = gather_observer_context(market_dir, session, market_label)

    client = Anthropic()
    response = client.messages.create(
        model=OBSERVER_MODEL,
        max_tokens=8192,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = ""
    for block in response.content:
        if hasattr(block, "text"):
            text += block.text
    return _extract_json(text)


def _editable_files(market_dir: Path) -> dict[str, Path]:
    files: dict[str, Path] = {}
    files["OBSERVER_GUIDANCE.md"] = market_dir / "OBSERVER_GUIDANCE.md"
    prompts_dir = market_dir / "prompts"
    if prompts_dir.is_dir():
        for path in sorted(prompts_dir.glob("*.txt")):
            files[str(path.relative_to(market_dir))] = path
    for name in ("pre-pipeline.py", "post-pipeline.py"):
        path = market_dir / name
        if path.is_file():
            files[name] = path
    return files


def _resolve_edit_path(market_dir: Path, rel_path: str) -> Path | None:
    rel = Path(rel_path)
    if rel_path.startswith("/") or ".." in rel.parts:
        return None
    allowed = _editable_files(market_dir)
    if rel_path in allowed:
        return allowed[rel_path]
    if rel_path == "OBSERVER_GUIDANCE.md":
        return market_dir / rel
    if len(rel.parts) == 2 and rel.parts[0] == "prompts" and rel.suffix == ".txt":
        return market_dir / rel
    return None


def _compile_python_files(paths: list[Path]) -> tuple[bool, str]:
    for path in paths:
        if path.suffix != ".py":
            continue
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as e:
            return False, str(e)
    return True, ""


def apply_file_updates(market_dir: Path, session: str, payload: dict, log_prefix: str = "worker") -> dict:
    """Apply allowlisted autonomous prompt/code updates and log the result."""
    reports_dir = market_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    updates = payload.get("file_updates") or []
    result = {
        "session": session,
        "applied": [],
        "rejected": [],
        "status": "no_updates",
        "change_log": payload.get("change_log") or "",
    }
    if not isinstance(updates, list) or not updates:
        (reports_dir / f"{session}-{log_prefix}-changes.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        return result

    backups: dict[Path, str] = {}
    touched: list[Path] = []
    for update in updates:
        if not isinstance(update, dict):
            result["rejected"].append({"reason": "update is not an object"})
            continue
        rel_path = str(update.get("path") or "")
        content = update.get("content")
        reason = str(update.get("reason") or "")
        path = _resolve_edit_path(market_dir, rel_path)
        if path is None:
            result["rejected"].append({"path": rel_path, "reason": "path is not allowlisted"})
            continue
        if not isinstance(content, str) or not content.strip():
            result["rejected"].append({"path": rel_path, "reason": "missing replacement content"})
            continue
        old_text = path.read_text(encoding="utf-8") if path.exists() else ""
        if path.suffix == ".py" and len(old_text) > EDITABLE_TEXT_LIMIT and len(content) < len(old_text) * 0.9:
            result["rejected"].append({
                "path": rel_path,
                "reason": "large Python file replacement is much shorter than current file",
            })
            continue
        backups.setdefault(path, old_text)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content.rstrip() + "\n", encoding="utf-8")
        touched.append(path)
        result["applied"].append({"path": rel_path, "reason": reason})

    ok, error = _compile_python_files(touched)
    if not ok:
        for path, old_text in backups.items():
            path.write_text(old_text, encoding="utf-8")
        result["status"] = "reverted"
        result["validation_error"] = error
    elif result["applied"]:
        result["status"] = "applied"
    elif result["rejected"]:
        result["status"] = "rejected"

    (reports_dir / f"{session}-{log_prefix}-changes.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return result


def apply_outputs(market_dir: Path, session: str, payload: dict) -> dict:
    day = market_dir / "data" / session

    if payload.get("improvement_md"):
        (day / f"{session}-improvement.md").write_text(
            payload["improvement_md"].strip() + "\n", encoding="utf-8"
        )

    if payload.get("journey_append_md"):
        journey_path = market_dir / "JOURNEY.md"
        existing = _read(journey_path)
        append = payload["journey_append_md"].strip()
        if append not in existing:
            with journey_path.open("a", encoding="utf-8") as f:
                f.write("\n\n" + append + "\n")

    if payload.get("strategy_md"):
        (market_dir / "STRATEGY.md").write_text(
            payload["strategy_md"].strip() + "\n", encoding="utf-8"
        )

    report = payload.get("report_md") or payload.get("daily_report") or payload.get("telegram_summary")
    if report:
        reports_dir = market_dir / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        report_path = reports_dir / f"{session}-daily-report.md"
        report_path.write_text(report.strip() + "\n", encoding="utf-8")

    return apply_file_updates(market_dir, session, payload)


def apply_observer_outputs(market_dir: Path, session: str, payload: dict) -> dict:
    reports_dir = market_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    wrote_guidance = False
    wrote_report = False
    if payload.get("observer_guidance_md"):
        (market_dir / "OBSERVER_GUIDANCE.md").write_text(
            payload["observer_guidance_md"].strip() + "\n", encoding="utf-8"
        )
        wrote_guidance = True

    if payload.get("observer_report_md"):
        (reports_dir / f"{session}-observer-report.md").write_text(
            payload["observer_report_md"].strip() + "\n", encoding="utf-8"
        )
        wrote_report = True

    result = apply_file_updates(market_dir, session, payload, log_prefix="observer")
    if result["status"] == "no_updates" and (wrote_guidance or wrote_report):
        result["status"] = "guidance_updated"
        (reports_dir / f"{session}-observer-changes.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    return result


def maybe_retry_post(market_key: str, market_dir: Path, session: str) -> bool:
    """If post output invalid, retry post-pipeline up to MAX_POST_RETRIES."""
    from automate.pipeline import run_post

    ok, _ = validate_post(market_dir, session)
    if ok:
        return True
    return run_post(market_key, market_dir, date.fromisoformat(session), MAX_POST_RETRIES)[0]


def _run_git(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )


def report_path(market_dir: Path, session: str) -> Path:
    return market_dir / "reports" / f"{session}-daily-report.md"


def _repo_web_base(remote_url: str) -> str:
    remote_url = remote_url.strip()
    if remote_url.endswith(".git"):
        remote_url = remote_url[:-4]
    if remote_url.startswith("git@") and ":" in remote_url:
        host, repo = remote_url[4:].split(":", 1)
        return f"https://{host}/{repo}"
    if remote_url.startswith("ssh://git@"):
        return "https://" + remote_url[len("ssh://git@"):]
    return remote_url


def build_report_url(report_file: Path) -> str:
    remote = _run_git(["config", "--get", "remote.origin.url"])
    branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    if remote.returncode != 0 or branch.returncode != 0:
        return ""
    base = _repo_web_base(remote.stdout)
    rel = report_file.relative_to(REPO_ROOT).as_posix()
    return f"{base}/blob/{quote(branch.stdout.strip(), safe='')}/{quote(rel, safe='/')}"


def git_commit_and_push_market(market_key: str, market_dir: Path, session: str) -> dict:
    """Commit and push worker-generated changes for one market folder."""
    result = {
        "status": "skipped",
        "market": market_key,
        "session": session,
        "message": "",
    }

    inside = _run_git(["rev-parse", "--is-inside-work-tree"])
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        result["message"] = "not a git repository"
        return result

    market_rel = str(market_dir.relative_to(REPO_ROOT))
    add = _run_git(["add", "--", market_rel])
    if add.returncode != 0:
        result["status"] = "failed"
        result["message"] = f"git add failed: {(add.stderr or add.stdout).strip()}"
        return result

    status = _run_git(["status", "--porcelain", "--", market_rel])
    if status.returncode != 0:
        result["status"] = "failed"
        result["message"] = f"git status failed: {(status.stderr or status.stdout).strip()}"
        return result
    if not status.stdout.strip():
        result["status"] = "no_changes"
        result["message"] = "no market changes to commit"
        return result

    commit_message = f"{market_key}: daily worker update {session}"
    commit = _run_git(["commit", "-m", commit_message])
    if commit.returncode != 0:
        result["status"] = "failed"
        result["message"] = f"git commit failed: {(commit.stderr or commit.stdout).strip()}"
        return result

    upstream = _run_git(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
    push_args = ["push"] if upstream.returncode == 0 else ["push", "-u", "origin", "HEAD"]
    push = _run_git(push_args)
    if push.returncode != 0:
        result["status"] = "committed_push_failed"
        result["message"] = f"commit created, push failed: {(push.stderr or push.stdout).strip()}"
        return result

    result["status"] = "pushed"
    result["message"] = commit_message
    result["report_url"] = build_report_url(report_path(market_dir, session))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", required=True, choices=["korean", "us"])
    parser.add_argument("--date", required=True, help="Session date YYYY-MM-DD")
    parser.add_argument("--skip-telegram", action="store_true")
    parser.add_argument("--skip-git", action="store_true", help="Do not auto git add/commit/push worker outputs")
    parser.add_argument("--skip-observer", action="store_true", help="Do not run the observer agent")
    parser.add_argument("--force-observer", action="store_true", help="Run observer even if cadence says it is not due")
    args = parser.parse_args()

    cfg = load_config()
    market_dir = REPO_ROOT / args.market
    label = "Korean (KRX)" if args.market == "korean" else "US (NYSE)"
    prefix = telegram_prefix(args.market)

    pre_ok, pre_errors = validate_pre(market_dir, args.date)
    if not pre_ok:
        details = "; ".join(pre_errors[:3]) or "pre-pipeline outputs missing"
        msg = (
            f"{prefix} ⏭️ {label} {args.date}: worker skipped\n"
            "Reason: pre-pipeline was not run or output is incomplete, so post-market/worker inputs are missing.\n"
            f"Details: {details}"
        )
        print(msg)
        if not args.skip_telegram:
            send_message(msg)
        return

    if not maybe_retry_post(args.market, market_dir, args.date):
        msg = f"{prefix} ⚠️ {label} {args.date}: post-pipeline failed after retries. Worker skipped."
        print(msg)
        if not args.skip_telegram:
            send_message(msg)
        sys.exit(1)

    print(f"[worker] Running for {args.market} session={args.date}")
    payload = run_worker(args.market, market_dir, args.date, label)
    update_result = apply_outputs(market_dir, args.date, payload)

    report = payload.get("report_md") or payload.get("daily_report") or payload.get("telegram_summary") or f"{label} {args.date}: worker completed (no report text)"
    telegram_summary = payload.get("telegram_summary") or payload.get("daily_report") or f"{label} {args.date}: worker completed."
    if update_result.get("status") in {"applied", "reverted", "rejected"}:
        update_note = f"Autonomous updates: {update_result['status']} ({len(update_result.get('applied', []))} applied, {len(update_result.get('rejected', []))} rejected)."
        report += f"\n\n{update_note}"
        telegram_summary += f"\n{update_note}"
        reports_dir = market_dir / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        report_path(market_dir, args.date).write_text(report.strip() + "\n", encoding="utf-8")

    interval_days = observer_interval_days(cfg)
    should_run_observer = (
        not args.skip_observer
        and (args.force_observer or observer_due(args.market, args.date, interval_days))
    )
    observer_result = {
        "status": "skipped",
        "message": "disabled by --skip-observer" if args.skip_observer else f"not due; interval={interval_days}d",
    }
    if should_run_observer:
        print(f"[observer] Running for {args.market} session={args.date}")
        observer_payload = run_observer(args.market, market_dir, args.date, label)
        observer_result = apply_observer_outputs(market_dir, args.date, observer_payload)
        mark_observer_ran(args.market, args.date)
        observer_note = (
            f"Observer: {observer_result['status']} "
            f"({len(observer_result.get('applied', []))} applied, {len(observer_result.get('rejected', []))} rejected)."
        )
        report += f"\n\n{observer_note}"
        if observer_payload.get("telegram_note"):
            telegram_summary += f"\n{observer_payload['telegram_note'].strip()}"
        telegram_summary += f"\n{observer_note}"
        report_path(market_dir, args.date).write_text(report.strip() + "\n", encoding="utf-8")

    print(f"\n--- Daily report ---\n{report}\n")

    git_result = {"status": "skipped", "message": "disabled by --skip-git"} if args.skip_git else git_commit_and_push_market(args.market, market_dir, args.date)
    print(f"[git] {git_result['status']}: {git_result.get('message', '')}")

    if not args.skip_telegram:
        header = f"{prefix} 📊 *{label}* — `{args.date}`\n\n"
        report_url = git_result.get("report_url") or ""
        link_line = f"\n\nToday's report: {report_url}" if report_url else ""
        send_message(header + telegram_summary + link_line + f"\n\nGit sync: {git_result['status']}")

    print("[worker] Done.")


if __name__ == "__main__":
    main()
