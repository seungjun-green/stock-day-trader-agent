#!/usr/bin/env python3
"""Print the report URL that Telegram would use after git push."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from automate.worker import build_report_url, report_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", choices=["korean", "us"], default="korean")
    parser.add_argument("--date", required=True, help="Session date YYYY-MM-DD")
    args = parser.parse_args()

    path = report_path(REPO_ROOT / args.market, args.date)
    url = build_report_url(path)
    if not url:
        print("report_url=unavailable (not a git repo, no origin, or no branch)")
        return 1
    print(f"report_url={url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
