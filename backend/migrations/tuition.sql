-- ════════════════════════════════════════════════════════════
--  PREMEDICAL TUITION — superadmin manages tuition + payments,
--  students see their own balance (read-only). Run once.
-- ════════════════════════════════════════════════════════════

-- Helper: is the current user a superadmin? (mirrors is_staff())
create or replace function is_superadmin()
returns boolean language sql security definer stable as $$
    select exists (select 1 from profiles where id = auth.uid() and role = 'superadmin');
$$;

-- General default + currency live in app_settings (snapshot source for new students).
insert into app_settings (key, value) values ('premed_tuition_default', '0') on conflict (key) do nothing;
insert into app_settings (key, value) values ('tuition_currency', 'NIS') on conflict (key) do nothing;

-- One tuition record per student (their snapshotted total + optional deadline).
create table if not exists student_tuition (
    student_id   uuid primary key references profiles(id) on delete cascade,
    total_amount numeric not null default 0,
    deadline     date,
    updated_at   timestamptz not null default now()
);

-- Recorded payments (installments). Paid = sum(amount); Left = total - paid.
create table if not exists tuition_payments (
    id         uuid primary key default gen_random_uuid(),
    student_id uuid not null references profiles(id) on delete cascade,
    amount     numeric not null,
    paid_on    date not null default current_date,
    note       text,
    created_by uuid references profiles(id),
    created_at timestamptz not null default now()
);
create index if not exists idx_tuition_payments_student on tuition_payments(student_id);

-- RLS: superadmin manages everything; a student may read only their own.
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
