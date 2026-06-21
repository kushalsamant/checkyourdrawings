-- Enable Row Level Security on public.users.
-- The backend connects via a direct Postgres connection (PLATFORM_DATABASE_URL)
-- as the table owner, which bypasses RLS, so the app is unaffected.
-- With RLS enabled and no policies, the public anon/authenticated API roles
-- (PostgREST) are denied all access by default, closing the anon-key exposure.

alter table public.users enable row level security;
