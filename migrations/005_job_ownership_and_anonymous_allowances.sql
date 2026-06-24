-- Job ownership (anonymous session + platform user) and lifetime anonymous allowances.

alter table public.comparison_jobs
    add column if not exists anon_session_id text,
    add column if not exists platform_user_id integer;

create index if not exists comparison_jobs_anon_session_idx
    on public.comparison_jobs (anon_session_id)
    where anon_session_id is not null;

create index if not exists comparison_jobs_user_email_status_idx
    on public.comparison_jobs (user_email, status)
    where user_email is not null;

create table if not exists public.anonymous_allowances (
    anon_session_id text primary key,
    successful_comparisons integer not null default 0,
    created_at timestamptz not null default now(),
    updated_at timestamptz,
    constraint anonymous_allowances_count_nonneg check (successful_comparisons >= 0)
);
