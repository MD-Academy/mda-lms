-- ════════════════════════════════════════════════════════════
--  TUITION v2 — price lives on each COURSE/PROGRAM, and balances
--  are tracked PER (student × program) with per-program currency.
--  Replaces the single global default from tuition.sql.
--
--  NOTE: this drops the old per-student tuition + payments (they
--  can't be auto-mapped to a specific program). Re-enter the few
--  you have from the Tuition page afterward.
-- ════════════════════════════════════════════════════════════

-- 1) Each course/program carries its own price + currency.
alter table courses add column if not exists tuition_amount   numeric;
alter table courses add column if not exists tuition_currency text default 'NIS';

-- 2) Recreate tuition tables keyed per (student, course).
drop table if exists tuition_payments cascade;
drop table if exists student_tuition cascade;

create table student_tuition (
    student_id   uuid not null references profiles(id) on delete cascade,
    course_id    uuid not null references courses(id) on delete cascade,
    total_amount numeric not null default 0,
    deadline     date,
    updated_at   timestamptz not null default now(),
    primary key (student_id, course_id)
);

create table tuition_payments (
    id         uuid primary key default gen_random_uuid(),
    student_id uuid not null references profiles(id) on delete cascade,
    course_id  uuid not null references courses(id) on delete cascade,
    amount     numeric not null,
    paid_on    date not null default current_date,
    note       text,
    created_by uuid references profiles(id),
    created_at timestamptz not null default now()
);
create index if not exists idx_tuition_payments_sc on tuition_payments(student_id, course_id);

-- 3) RLS: superadmin manages everything; a student reads only their own.
alter table student_tuition enable row level security;
alter table tuition_payments enable row level security;

drop policy if exists student_tuition_super on student_tuition;
create policy student_tuition_super on student_tuition
    for all using (is_superadmin()) with check (is_superadmin());
drop policy if exists student_tuition_own on student_tuition;
create policy student_tuition_own on student_tuition
    for select using (auth.uid() = student_id);

drop policy if exists tuition_payments_super on tuition_payments;
create policy tuition_payments_super on tuition_payments
    for all using (is_superadmin()) with check (is_superadmin());
drop policy if exists tuition_payments_own on tuition_payments;
create policy tuition_payments_own on tuition_payments
    for select using (auth.uid() = student_id);

-- (The old app_settings keys premed_tuition_default / tuition_currency are no
--  longer used; harmless to leave in place.)
