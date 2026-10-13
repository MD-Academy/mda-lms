-- ════════════════════════════════════════════════════════════
--  SECTION TIME — per-student time tracking for individual parts of the
--  portal (a subject page, taking a quiz, taking an exam, ...). Forward-
--  looking only — one row per page view, started on load and closed on
--  unload, same mechanism as login_sessions.
--  Idempotent: safe to run even though the table may already exist.
--  The student browser inserts/updates its OWN rows; staff read all.
-- ════════════════════════════════════════════════════════════

create table if not exists section_sessions (
    id           uuid primary key default gen_random_uuid(),
    student_id   uuid not null references profiles(id) on delete cascade,
    section_type text not null,      -- 'subject' | 'quiz' | 'exam' | ... (more added over time)
    section_ref  text,               -- the room/quiz/exam id this page view was for, if any
    started_at   timestamptz not null default now(),
    last_seen_at timestamptz,
    ended_at     timestamptz
);
create index if not exists idx_section_sessions_student on section_sessions(student_id, started_at desc);

alter table section_sessions enable row level security;

-- A student may create, read and update only their OWN rows.
-- (Read-own is required because the app does insert(...).select('id') and
--  updates by id during the heartbeat — without it, tracking fails silently.)
drop policy if exists section_sessions_student_insert on section_sessions;
create policy section_sessions_student_insert on section_sessions
    for insert to authenticated with check (auth.uid() = student_id);

drop policy if exists section_sessions_student_select on section_sessions;
create policy section_sessions_student_select on section_sessions
    for select using (auth.uid() = student_id);

drop policy if exists section_sessions_student_update on section_sessions;
create policy section_sessions_student_update on section_sessions
    for update using (auth.uid() = student_id) with check (auth.uid() = student_id);

-- Staff (admin/superadmin) read everyone's section time for the Activity report.
drop policy if exists section_sessions_staff_select on section_sessions;
create policy section_sessions_staff_select on section_sessions
    for select using (is_staff());
