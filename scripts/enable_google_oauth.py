#!/usr/bin/env python3
"""Enable Google OAuth on the linked Supabase project via Management API.

The Management API returns external_google_secret as a SHA256 hash on GET.
You must supply the plaintext Google OAuth client secret via GOOGLE_OAUTH_CLIENT_SECRET.
Copy it from Google Cloud Console > Credentials > OAuth 2.0 Client IDs.
"""

from __future__ import annotations

import os
import sys

import httpx

PROJECT_REF = "ytcnzhapqainbtkoshvh"
SOURCE_PROJECT_REF = "twxudlzipbiavnzcitzb"
CALLBACK_URI = f"https://{PROJECT_REF}.supabase.co/auth/v1/callback"
GOOGLE_CLIENT_ID = (
    "620186529337-lrr0bflcuihq2gnsko6vbrnsdv2u3ugu.apps.googleusercontent.com"
)


def _load_supabase_token() -> str:
    try:
        import win32cred
    except ImportError as exc:
        raise RuntimeError("Install pywin32 to read the Supabase CLI token.") from exc

    credential = win32cred.CredRead("Supabase CLI:supabase", win32cred.CRED_TYPE_GENERIC)
    return credential["CredentialBlob"].decode("utf-8").strip()


def main() -> int:
    google_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "").strip()
    if not google_secret:
        print(
            "Set GOOGLE_OAUTH_CLIENT_SECRET to the plaintext client secret from "
            "Google Cloud Console, then re-run this script.",
            file=sys.stderr,
        )
        print(
            "Dashboard fallback: Supabase > Authentication > Providers > Google",
            file=sys.stderr,
        )
        print(
            f"If sign-in fails, add this redirect URI in Google Cloud Console:\n  {CALLBACK_URI}",
            file=sys.stderr,
        )
        return 1

    token = _load_supabase_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    with httpx.Client(timeout=30.0) as client:
        response = client.patch(
            f"https://api.supabase.com/v1/projects/{PROJECT_REF}/config/auth",
            headers=headers,
            json={
                "external_google_enabled": True,
                "external_google_client_id": GOOGLE_CLIENT_ID,
                "external_google_secret": google_secret,
                "external_google_skip_nonce_check": False,
            },
        )
        response.raise_for_status()
        data = response.json()

    print(f"google_enabled={data.get('external_google_enabled')}")
    print(f"client_id={data.get('external_google_client_id')}")
    print(f"callback_uri={CALLBACK_URI}")
    print("secret_applied=ok")
    print()
    print("Test Sign in on https://checkyourdrawings.kvshvl.in/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
