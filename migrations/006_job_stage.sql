-- Live compare progress: stage text exposed on GET /jobs/{id}.

alter table public.comparison_jobs
    add column if not exists stage text;
