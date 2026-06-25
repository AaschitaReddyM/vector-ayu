-- ============================================================================
-- VAYU migration: switch patient identifiers from UUID -> TEXT (e.g. 'PT-0001')
--
-- Run this ONCE in the Supabase SQL Editor if you already ran the original
-- (UUID) version of schema.sql. Safe on the empty demo tables.
-- Idempotent: re-running is harmless.
-- ============================================================================

-- 1. Drop the foreign keys that point at patients.id
alter table public.risk_scores   drop constraint if exists risk_scores_patient_id_fkey;
alter table public.triage_queue  drop constraint if exists triage_queue_patient_id_fkey;
alter table public.outreach_logs drop constraint if exists outreach_logs_patient_id_fkey;

-- 2. Convert patients.id to text and drop the auto-UUID default
alter table public.patients alter column id drop default;
alter table public.patients alter column id type text using id::text;

-- 3. Convert the child patient_id columns to text
alter table public.risk_scores   alter column patient_id type text using patient_id::text;
alter table public.triage_queue  alter column patient_id type text using patient_id::text;
alter table public.outreach_logs alter column patient_id type text using patient_id::text;

-- 4. Re-create the foreign keys
alter table public.risk_scores
  add constraint risk_scores_patient_id_fkey
  foreign key (patient_id) references public.patients (id) on delete cascade;

alter table public.triage_queue
  add constraint triage_queue_patient_id_fkey
  foreign key (patient_id) references public.patients (id) on delete cascade;

alter table public.outreach_logs
  add constraint outreach_logs_patient_id_fkey
  foreign key (patient_id) references public.patients (id) on delete cascade;

-- ============================================================================
-- End of migration
-- ============================================================================
