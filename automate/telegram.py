"""Send Telegram notifications."""
from __future__ import annotations

import os
import textwrap

import requests


def send_message(text: str, parse_mode: str = "Markdown") -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("[telegram] TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set — skipping send")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    chunks = _split_message(text, 4000)
    ok = True
    for chunk in chunks:
        resp = requests.post(
            url,
            json={"chat_id": chat_id, "text": chunk, "parse_mode": parse_mode},
            timeout=30,
        )
        if not resp.ok:
            # Retry without markdown if parse failed
            if parse_mode and resp.status_code == 400:
                resp = requests.post(
                    url,
                    json={"chat_id": chat_id, "text": chunk},
                    timeout=30,
                )
            if not resp.ok:
                print(f"[telegram] send failed: {resp.status_code} {resp.text[:200]}")
                ok = False
    return ok


def _split_message(text: str, limit: int) -> list[str]:
    if len(text) <= limit:
        return [text]
    parts = []
    while text:
        if len(text) <= limit:
            parts.append(text)
            break
        cut = text.rfind("\n", 0, limit)
        if cut < limit // 2:
            cut = limit
        parts.append(text[:cut])
        text = text[cut:].lstrip("\n")
    return parts
