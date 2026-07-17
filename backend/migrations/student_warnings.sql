-- ════════════════════════════════════════════════════════════
--  STUDENT WARNINGS — permanent, tamper-proof audit trail of every
--  warning the system sent a student (low attendance / low grade).
--  Proof for disputes: who, exact time, course, detail, email + status.
--  Written ONLY by the backend (service role). Staff read-only.
--  Kept indefinitely. Run once in the Supabase SQL editor.
-- ════════════════════════════════════════════════════════════

create table if not exists student_warnings (
    id           uuid primary key default gen_random_uuid(),
    student_id   uuid references profiles(id) on delete set null,   -- keep record even if the account is later deleted
    student_name text,                                              -- snapshot
    type         text not null,          -- 'attendance_low' | 'grade_low'
    course_id    uuid,
    course_name  text,                   -- snapshot
    detail       text not null,          -- human-readable, e.g. "Attendance 62% (8 of 13) — below the required 80%"
    channel      text not null default 'email',
    email_to     text,
    subject      text,
    delivered    boolean not null default false,
    created_at   timestamptz not null default now()
);
create index if not exists idx_student_warnings_student on student_warnings(student_id, created_at desc);

grant select on student_warnings to authenticated;   -- staff read via RLS; NO client writes
grant all on student_warnings to service_role;

alter table student_warnings enable row level security;

-- Staff can READ; nobody can insert/update/delete from the client (only the backend service role).
drop policy if exists sw_staff_read on student_warnings;
create policy sw_staff_read on student_warnings for select using (is_staff());

-- Global passing minimum for grade warnings (default 60%). Super-admin sets it in the Gradebook.
insert into app_settings (key, value) values ('grade_pass_min', '60') on conflict (key) do nothing;
