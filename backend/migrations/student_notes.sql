-- ════════════════════════════════════════════════════════════
--  TEACHER FEEDBACK — free-form notes a teacher writes to a student
--  whenever they judge it useful. Nothing to do with an exam, a quiz
--  or an oral presentation: a teacher notices after a class that a
--  student is struggling, and writes it down. It becomes a running,
--  dated log the student sees in their portal and in the bell.
--
--  course_id is OPTIONAL: leave it null for general feedback, or set
--  it to tie the note to one course (then it also shows on that
--  course page next to the student's grades).
--
--  Safe to re-run. Run in the Supabase SQL editor.
-- ════════════════════════════════════════════════════════════

create table if not exists student_notes (
    id                 uuid primary key default gen_random_uuid(),
    student_id         uuid not null references profiles(id) on delete cascade,
    course_id          uuid references courses(id) on delete cascade,   -- null = general feedback
    body               text not null,                    -- the feedback itself
    visible_to_student boolean not null default true,    -- unticked = internal note for staff only
    author_id          uuid,                             -- who wrote it
    author_name        text,                             -- snapshot: students can't read staff profiles
    created_at         timestamptz not null default now(),   -- never changes — this is the record
    edited_at          timestamptz,                       -- set only if the author corrects the wording
    emailed_at         timestamptz                        -- when the student was emailed (sent once, never re-sent)
);

-- If an earlier version of this table was created with course_id NOT NULL, relax it.
alter table student_notes alter column course_id drop not null;
alter table student_notes add column if not exists emailed_at timestamptz;

create index if not exists idx_student_notes_student on student_notes(student_id, created_at desc);
create index if not exists idx_student_notes_course  on student_notes(course_id);

grant select, insert, update, delete on student_notes to authenticated;
grant all on student_notes to service_role;

alter table student_notes enable row level security;

-- Staff write and read everything (including internal notes).
drop policy if exists sn_staff_all on student_notes;
create policy sn_staff_all on student_notes for all using (is_staff()) with check (is_staff());

-- A student reads only their OWN entries, and only the shared ones.
drop policy if exists sn_student_own on student_notes;
create policy sn_student_own on student_notes for select using (
    student_id = auth.uid() and visible_to_student = true
);

-- ── Bell notifications ──
-- Let a student mark a feedback entry as read, alongside announcements
-- and upcoming classes.
alter table notification_reads drop constraint if exists notification_reads_kind_check;
alter table notification_reads add constraint notification_reads_kind_check
    check (kind in ('announcement', 'schedule', 'feedback'));
