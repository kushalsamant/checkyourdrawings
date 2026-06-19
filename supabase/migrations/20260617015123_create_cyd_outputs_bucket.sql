-- Pass 2: cyd_outputs bucket, RLS, and comparisons metadata table.

insert into storage.buckets (id, name, public)
values ('cyd_outputs', 'cyd_outputs', true)
on conflict (id) do nothing;

create table if not exists public.comparisons (
    id uuid primary key,
    user_id integer not null,
    storage_path text not null,
    metadata jsonb,
    created_at timestamptz not null default now()
);

create index if not exists comparisons_user_id_idx on public.comparisons (user_id);

alter table public.comparisons enable row level security;

drop policy if exists "Service role manages comparisons" on public.comparisons;

create policy "Service role manages comparisons"
on public.comparisons
for all
to service_role
using (true)
with check (true);
