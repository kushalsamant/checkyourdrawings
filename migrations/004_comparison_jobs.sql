-- Async comparison jobs for checkyourdrawings (shared platform Postgres).

create table if not exists public.comparison_jobs (
    id uuid primary key default gen_random_uuid(),
    status text not null default 'pending',
    priority integer not null default 0,
    user_email text,
    drawing_a_path text not null,
    drawing_b_path text not null,
    drawing_a_name text not null,
    drawing_b_name text not null,
    result jsonb,
    error_message text,
    created_at timestamptz not null default now(),
    started_at timestamptz,
    completed_at timestamptz,
    constraint comparison_jobs_status_check check (
        status in ('pending', 'running', 'completed', 'failed')
    )
);

create index if not exists comparison_jobs_queue_idx
    on public.comparison_jobs (status, priority desc, created_at asc);

create index if not exists comparison_jobs_created_at_idx
    on public.comparison_jobs (created_at);
