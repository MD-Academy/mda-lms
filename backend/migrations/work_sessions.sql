-- ════════════════════════════════════════════════════════════
--  STAFF WORK HOURS — tamper-proof clock in/out for teachers/admins.
--  Times are stamped by the backend (service role); admins have NO
--  write access to this table, so nothing can be backdated or edited
--  after clock-out. Admins read their OWN sessions; super-admin reads
--  everyone's for the report. Run once in the Supabase SQL editor.
-- ════════════════════════════════════════════════════════════

create table if not exists work_sessions (
    id          uuid primary key default gen_random_uuid(),
    admin_id    uuid not null references profiles(id) on delete cascade,
    started_at  timestamptz not null,
    ended_at    timestamptz,          -- null while the session is open
    note        text,
    created_at  timestamptz not null default now()
);
create index if not exists idx_work_sessions_admin on work_sessions(admin_id, started_at desc);
create index if not exists idx_work_sessions_open  on work_sessions(admin_id) where ended_at is null;

-- Reads only for signed-in users; ALL writes go through the backend service role.
grant select on work_sessions to authenticated;
grant all on work_sessions to service_role;

alter table work_sessions enable row level security;

-- Admins read their OWN sessions.
drop policy if exists ws_admin_own_read on work_sessions;
create policy ws_admin_own_read on work_sessions for select using (admin_id = auth.uid());

-- Super-admin reads EVERYONE's (for the report).
drop policy if exists ws_super_read on work_sessions;
create policy ws_super_read on work_sessions for select using (is_superadmin());

-- NOTE: intentionally no INSERT/UPDATE/DELETE policy → admins cannot write
-- directly. The backend (service role) is the only writer, and it stamps
-- started_at / ended_at with server time.
