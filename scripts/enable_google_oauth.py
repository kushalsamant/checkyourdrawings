#!/usr/bin/env python3
"""Enable Google OAuth on the linked Supabase project via Management API."""

from __future__ import annotations

import sys

import httpx

PROJECT_REF = "ytcnzhapqainbtkoshvh"
SOURCE_PROJECT_REF = "twxudlzipbiavnzcitzb"
CALLBACK_URI = f"https://{PROJECT_REF}.supabase.co/auth/v1/callback"


def _load_supabase_token() -> str:
    try:
        import win32cred
    except ImportError as exc:
        raise RuntimeError("Install pywin32 to read the Supabase CLI token.") from exc

    credential = win32cred.CredRead("Supabase CLI:supabase", win32cred.CRED_TYPE_GENERIC)
    return credential["CredentialBlob"].decode("utf-8").strip()


def main() -> int:
    token = _load_supabase_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    with httpx.Client(timeout=30.0) as client:
        source = client.get(
            f"https://api.supabase.com/v1/projects/{SOURCE_PROJECT_REF}/config/auth",
            headers=headers,
        )
        source.raise_for_status()
        google_client_id = source.json()["external_google_client_id"]
        google_secret = source.json()["external_google_secret"]
        if not google_client_id or not google_secret:
            print("Source project has no Google OAuth credentials.", file=sys.stderr)
            return 1

        response = client.patch(
            f"https://api.supabase.com/v1/projects/{PROJECT_REF}/config/auth",
            headers=headers,
            json={
                "external_google_enabled": True,
                "external_google_client_id": google_client_id,
                "external_google_secret": google_secret,
                "external_google_skip_nonce_check": False,
            },
        )
        response.raise_for_status()
        data = response.json()

    print(f"google_enabled={data.get('external_google_enabled')}")
    print(f"client_id={data.get('external_google_client_id')}")
    print(f"callback_uri={CALLBACK_URI}")
    print(
        "Add the callback URI to the Google OAuth client in Cloud Console, "
        "then test Sign in on https://checkyourdrawings.kvshvl.in/"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
