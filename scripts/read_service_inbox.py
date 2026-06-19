#!/usr/bin/env python3
"""List recent Gmail messages via IMAP (read-only). Uses stdlib only.

Setup:
  1. Gmail → Settings → Forwarding and POP/IMAP → Enable IMAP
  2. Google Account → App password for Mail
  3. Add to gitignored .env:
       GMAIL_IMAP_USER=you@gmail.com
       GMAIL_IMAP_APP_PASSWORD=xxxx xxxx xxxx xxxx

Usage:
  python scripts/read_service_inbox.py
  python scripts/read_service_inbox.py --limit 20 --from render.com,vercel.com
"""

from __future__ import annotations

import argparse
import email
import imaplib
import os
import sys
from email.header import decode_header
from email.message import Message
from pathlib import Path


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def _decode_header_value(value: str | None) -> str:
    if not value:
        return ""
    parts: list[str] = []
    for chunk, encoding in decode_header(value):
        if isinstance(chunk, bytes):
            parts.append(chunk.decode(encoding or "utf-8", errors="replace"))
        else:
            parts.append(chunk)
    return "".join(parts)


def _message_snippet(message: Message, max_len: int = 160) -> str:
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_type() != "text/plain":
                continue
            payload = part.get_payload(decode=True)
            if isinstance(payload, bytes):
                text = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
                return " ".join(text.split())[:max_len]
        return ""
    payload = message.get_payload(decode=True)
    if not isinstance(payload, bytes):
        return ""
    text = payload.decode(message.get_content_charset() or "utf-8", errors="replace")
    return " ".join(text.split())[:max_len]


def _matches_sender(from_header: str, filters: list[str]) -> bool:
    if not filters:
        return True
    lowered = from_header.lower()
    return any(token.lower() in lowered for token in filters)


def main() -> int:
    parser = argparse.ArgumentParser(description="List recent Gmail inbox messages (read-only).")
    parser.add_argument("--limit", type=int, default=20, help="Max messages to print (default: 20)")
    parser.add_argument(
        "--from",
        dest="from_filters",
        default="",
        help="Comma-separated sender substrings, e.g. render.com,vercel.com",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    _load_dotenv(repo_root / ".env")

    user = os.environ.get("GMAIL_IMAP_USER", "").strip()
    password = os.environ.get("GMAIL_IMAP_APP_PASSWORD", "").replace(" ", "")
    if not user or not password:
        print(
            "Set GMAIL_IMAP_USER and GMAIL_IMAP_APP_PASSWORD in .env "
            "(see script header and .env.example).",
            file=sys.stderr,
        )
        return 1

    filters = [part.strip() for part in args.from_filters.split(",") if part.strip()]

    with imaplib.IMAP4_SSL("imap.gmail.com") as client:
        client.login(user, password)
        client.select("INBOX")
        status, data = client.search(None, "ALL")
        if status != "OK" or not data or not data[0]:
            print("No messages found.")
            return 0

        ids = data[0].split()
        shown = 0
        for message_id in reversed(ids):
            if shown >= args.limit:
                break
            status, fetched = client.fetch(message_id, "(RFC822)")
            if status != "OK" or not fetched:
                continue
            raw = fetched[0]
            if not isinstance(raw, tuple) or len(raw) < 2:
                continue
            message = email.message_from_bytes(raw[1])
            from_header = _decode_header_value(message.get("From"))
            if not _matches_sender(from_header, filters):
                continue
            date_header = _decode_header_value(message.get("Date"))
            subject = _decode_header_value(message.get("Subject"))
            snippet = _message_snippet(message)
            print(f"{date_header}\t{from_header}\t{subject}")
            if snippet:
                print(f"  {snippet}")
            shown += 1

        if shown == 0:
            print("No messages matched the requested filters.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
