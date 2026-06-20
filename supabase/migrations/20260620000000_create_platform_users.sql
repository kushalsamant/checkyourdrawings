-- Platform users table for auth and subscription gating.

create table if not exists public.users (
    id serial primary key,
    email text not null unique,
    name text,
    google_id text unique,
    credits integer default 5,
    subscription_tier text default 'trial',
    subscription_status text default 'active',
    razorpay_customer_id text unique,
    razorpay_subscription_id text,
    subscription_auto_renew boolean default false,
    subscription_expires_at timestamptz,
    created_at timestamptz default now(),
    updated_at timestamptz,
    last_login timestamptz,
    is_active boolean default true
);

create index if not exists users_email_idx on public.users (email);
create index if not exists users_google_id_idx on public.users (google_id);
create index if not exists users_razorpay_customer_id_idx on public.users (razorpay_customer_id);
create index if not exists users_razorpay_subscription_id_idx on public.users (razorpay_subscription_id);
