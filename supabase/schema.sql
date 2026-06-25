-- ============================================================================
-- VAYU Predictive Healthcare Triage — Supabase / PostgreSQL schema
-- Paste directly into the Supabase SQL Editor and run.
--
-- Includes: UUID primary keys, created_at/updated_at timestamps (with an
-- auto-update trigger), foreign keys, helpful indexes, and Row Level Security
-- policies granting access to authenticated users.
-- The script is idempotent (safe to re-run).
-- ============================================================================

-- ---------------------------------------------------------------------------
-- Extensions (gen_random_uuid lives in pgcrypto; present by default on Supabase)
-- ---------------------------------------------------------------------------
create extension if not exists "pgcrypto";

-- ---------------------------------------------------------------------------
-- Shared trigger: keep updated_at current on every UPDATE
-- ---------------------------------------------------------------------------
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- ===========================================================================
-- 1. patients
-- ===========================================================================
create table if not exists public.patients (
  id               text primary key,   -- business key, e.g. 'PT-0001'
  given_name       text,
  family_name      text,
  birth_date       date,
  gender           text,
  postal_code      text,
  primary_language text,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now()
);

drop trigger if exists trg_patients_updated_at on public.patients;
create trigger trg_patients_updated_at
  before update on public.patients
  for each row execute function public.set_updated_at();

-- ===========================================================================
-- 2. risk_scores
-- ===========================================================================
create table if not exists public.risk_scores (
  id                       uuid primary key default gen_random_uuid(),
  patient_id               text not null references public.patients (id) on delete cascade,
  probabilities            jsonb,   -- e.g. {"respiratory":0.31,"cardiovascular":0.12,"metabolic":0.08}
  climate_volatility_delta jsonb,   -- per-head deltas, same key structure as probabilities
  combined_delta           double precision,
  top_head                 text,
  scored_at                timestamptz not null default now(),
  created_at               timestamptz not null default now(),
  updated_at               timestamptz not null default now()
);

create index if not exists idx_risk_scores_patient_id on public.risk_scores (patient_id);
create index if not exists idx_risk_scores_scored_at  on public.risk_scores (scored_at desc);

drop trigger if exists trg_risk_scores_updated_at on public.risk_scores;
create trigger trg_risk_scores_updated_at
  before update on public.risk_scores
  for each row execute function public.set_updated_at();

-- ===========================================================================
-- 3. triage_queue
-- ===========================================================================
create table if not exists public.triage_queue (
  id           uuid primary key default gen_random_uuid(),
  patient_id   text not null references public.patients (id) on delete cascade,
  risk_total   double precision,
  head         text,
  status       text not null default 'deferred'
               check (status in ('accepted', 'deferred', 'completed')),
  triage_date  date not null default current_date,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);

create index if not exists idx_triage_queue_patient_id on public.triage_queue (patient_id);
create index if not exists idx_triage_queue_status     on public.triage_queue (status);
create index if not exists idx_triage_queue_date       on public.triage_queue (triage_date desc);

drop trigger if exists trg_triage_queue_updated_at on public.triage_queue;
create trigger trg_triage_queue_updated_at
  before update on public.triage_queue
  for each row execute function public.set_updated_at();

-- ===========================================================================
-- 4. outreach_logs
-- ===========================================================================
create table if not exists public.outreach_logs (
  id              uuid primary key default gen_random_uuid(),
  patient_id      text not null references public.patients (id) on delete cascade,
  track           text,   -- e.g. 'Track A Auto', 'Track B Manual'
  message_content text,
  sent_at         timestamptz not null default now(),
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

create index if not exists idx_outreach_logs_patient_id on public.outreach_logs (patient_id);
create index if not exists idx_outreach_logs_sent_at    on public.outreach_logs (sent_at desc);

drop trigger if exists trg_outreach_logs_updated_at on public.outreach_logs;
create trigger trg_outreach_logs_updated_at
  before update on public.outreach_logs
  for each row execute function public.set_updated_at();

-- ===========================================================================
-- Row Level Security
-- Enable RLS on every table and allow full access to authenticated users.
-- (Tighten these later — e.g. scope rows to a clinician/org — for production.)
-- ===========================================================================
alter table public.patients      enable row level security;
alter table public.risk_scores   enable row level security;
alter table public.triage_queue  enable row level security;
alter table public.outreach_logs enable row level security;

-- patients
drop policy if exists "authenticated_all_patients" on public.patients;
create policy "authenticated_all_patients"
  on public.patients
  for all
  to authenticated
  using (true)
  with check (true);

-- risk_scores
drop policy if exists "authenticated_all_risk_scores" on public.risk_scores;
create policy "authenticated_all_risk_scores"
  on public.risk_scores
  for all
  to authenticated
  using (true)
  with check (true);

-- triage_queue
drop policy if exists "authenticated_all_triage_queue" on public.triage_queue;
create policy "authenticated_all_triage_queue"
  on public.triage_queue
  for all
  to authenticated
  using (true)
  with check (true);

-- outreach_logs
drop policy if exists "authenticated_all_outreach_logs" on public.outreach_logs;
create policy "authenticated_all_outreach_logs"
  on public.outreach_logs
  for all
  to authenticated
  using (true)
  with check (true);

-- ============================================================================
-- End of schema
-- ============================================================================
