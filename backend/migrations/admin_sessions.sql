-- ════════════════════════════════════════════════════════════
--  ADMIN LOGIN ACTIVITY — mirrors login_sessions, but for staff
--  usage of the admin panel (not payroll clock-in/out, which is
--  work_sessions). The admin browser inserts/updates its OWN
--  session; only superadmins read everyone's, for the usage
--  overview report. Run once in the Supabase SQL editor.
-- ════════════════════════════════════════════════════════════

create table if not exists admin_sessions (
    id           uuid primary key default gen_random_uuid(),
    admin_id     uuid not null references profiles(id) on delete cascade,
    started_at   timestamptz not null default now(),
    last_seen_at timestamptz,
    ended_at     timestamptz
);
create index if not exists idx_admin_sessions_admin on admin_sessions(admin_id, started_at desc);

alter table admin_sessions enable row level security;

-- A staff member may create, read and update only their OWN sessions.
drop policy if exists admin_sessions_own_insert on admin_sessions;
create policy admin_sessions_own_insert on admin_sessions
    for insert to authenticated with check (auth.uid() = admin_id);

drop policy if exists admin_sessions_own_select on admin_sessions;
create policy admin_sessions_own_select on admin_sessions
    for select using (auth.uid() = admin_id);

drop policy if exists admin_sessions_own_update on admin_sessions;
create policy admin_sessions_own_update on admin_sessions
    for update using (auth.uid() = admin_id) with check (auth.uid() = admin_id);

-- Only superadmins read everyone's sessions, for the Usage Analytics report.
drop policy if exists admin_sessions_super_select on admin_sessions;
create policy admin_sessions_super_select on admin_sessions
    for select using (is_superadmin());
