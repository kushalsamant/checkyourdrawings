# Manual operations checklist

Tasks that require your Google Cloud account, contacts, or DNS — not repo code.

## 1. Google OAuth consent screen branding

**Why:** Google may show `ytcnzhapqainbtkoshvh.supabase.co` on the sign-in screen. Branding improves trust until unified kvshvl.in sign-in ships.

**Steps (Google Cloud Console):**

1. Open [Google Cloud Console](https://console.cloud.google.com/) → project with **KVSHVL (Production)** OAuth client.
2. **APIs & Services** → **OAuth consent screen**.
3. Set:
   - **App name:** `KVSHVL`
   - **User support email:** your email
   - **App logo:** kvshvl logo (square, min 120×120)
   - **Application home page:** `https://kvshvl.in`
   - **Application privacy policy:** `https://kvshvl.in` (or dedicated policy URL if you have one)
   - **Authorized domains:** `kvshvl.in`, `checkyourdrawings.kvshvl.in`
4. Save. Test sign-in from https://checkyourdrawings.kvshvl.in → **Sign in**.

**Note:** The Supabase callback host may still appear on one line of the Google prompt. That is expected while CYD uses per-app Supabase OAuth. Full fix = unified kvshvl.in sign-in (see [deploy.md](deploy.md) §4).

**Checklist:**

- [ ] App name set to KVSHVL
- [ ] Logo uploaded
- [ ] Homepage `https://kvshvl.in`
- [ ] Test sign-in from production CYD

---

## 2. Friend share outreach

**Why:** Validate whether batch + ZIP alone is worth paying for before pricing on kvshvl.in.

**URL:** https://checkyourdrawings.kvshvl.in

**Suggested message (WhatsApp / email):**

> I built a small tool for coordination — upload two drawing PDFs (revision A vs B) and get a color overlay in ~30 seconds. Free for single pairs, no sign-in.
>
> https://checkyourdrawings.kvshvl.in
>
> If you ever run a full revision stack (10+ pairs), there is a batch mode behind kvshvl subscription — I'd love to know if that would save you time and what you'd pay from project budget.

**Ask:**

- Single compare vs batch need?
- Typical filenames / pairing workflow?
- Would they pay for batch + ZIP only (same PNG quality as free)?

**Track feedback** (spreadsheet or notes):

| Contact | Single useful? | Batch need? | Pay signal | Notes |
|---------|----------------|-------------|------------|-------|
| | | | | |

**Checklist:**

- [ ] Sent to ~10 coordination contacts
- [ ] Collected at least 3 responses
- [ ] Decided whether batch alone is enough paid wedge

---

## 3. Optional API custom domain

**Current:** API lives at `https://checkyourdrawings.onrender.com` (canonical in all docs).

**Optional:** CNAME `api.checkyourdrawings.kvshvl.in` → Render service custom domain. Then update Vercel `VITE_API_BASE_URL` and Render `CYD_CORS_ORIGINS` if you switch.

**Checklist:**

- [ ] Skip (onrender.com is fine), **or**
- [ ] Add DNS CNAME in kvshvl.in zone → Render custom domain → update env vars

---

## 4. Portfolio link (kvshvl.in)

**Status:** Side tab CTA already links to Check Your Drawings in [`kushalsamant.github.io/_includes/side-tabs.html`](../../kushalsamant.github.io/_includes/side-tabs.html).

Optional: add a project card on the portfolio homepage — edit the portfolio repo separately.
