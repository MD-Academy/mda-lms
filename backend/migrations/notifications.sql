-- ════════════════════════════════════════════════════════════
--  STUDENT NOTIFICATIONS (bell) — track which announcements and
--  upcoming classes a student has seen. Run once in SQL editor.
-- ════════════════════════════════════════════════════════════

-- One-time "start fresh" flag: on a student's first load with the bell, we
-- baseline everything that already exists as read, so the bell only lights up
-- for genuinely new activity afterward.
alter table profiles add column if not exists notifs_init boolean not null default false;

-- One row per (student, item) the student has dismissed/seen.
create table if not exists notification_reads (
    student_id uuid not null references profiles(id) on delete cascade,
    kind       text not null check (kind in ('announcement', 'schedule')),
    ref_id     uuid not null,
    read_at    timestamptz not null default now(),
    primary key (student_id, kind, ref_id)
);

alter table notification_reads enable row level security;

-- A student manages only their own read-marks (insert/select/update/delete).
drop policy if exists notif_reads_own on notification_reads;
create policy notif_reads_own on notification_reads
    for all using (auth.uid() = student_id) with check (auth.uid() = student_id);
