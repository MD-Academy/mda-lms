-- ════════════════════════════════════════════════════════════
--  LOGIN ACTIVITY — per-student session tracking (student portal).
--  Idempotent: safe to run even though the table may already exist.
--  The student browser inserts/updates its OWN session; staff read all.
-- ════════════════════════════════════════════════════════════

create table if not exists login_sessions (
    id           uuid primary key default gen_random_uuid(),
    student_id   uuid not null references profiles(id) on delete cascade,
    started_at   timestamptz not null default now(),
    last_seen_at timestamptz,
    ended_at     timestamptz
);
create index if not exists idx_login_sessions_student on login_sessions(student_id, started_at desc);

alter table login_sessions enable row level security;

-- A student may create, read and update only their OWN sessions.
-- (Read-own is required because the app does insert(...).select('id') and
--  updates by id during the heartbeat — without it, tracking fails silently.)
drop policy if exists login_sessions_student_insert on login_sessions;
create policy login_sessions_student_insert on login_sessions
    for insert to authenticated with check (auth.uid() = student_id);

drop policy if exists login_sessions_student_select on login_sessions;
create policy login_sessions_student_select on login_sessions
    for select using (auth.uid() = student_id);

drop policy if exists login_sessions_student_update on login_sessions;
create policy login_sessions_student_update on login_sessions
    for update using (auth.uid() = student_id) with check (auth.uid() = student_id);

-- Staff (admin/superadmin) read everyone's sessions for the Login Activity report.
drop policy if exists login_sessions_staff_select on login_sessions;
create policy login_sessions_staff_select on login_sessions
    for select using (is_staff());
