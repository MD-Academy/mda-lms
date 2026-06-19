-- ════════════════════════════════════════════════════════════
--  GRADUATION: Diploma + Recommendation Letter
--  Run this once in the Supabase SQL editor.
-- ════════════════════════════════════════════════════════════

-- 1) Which exams count toward graduation / the final GPA.
--    Defaults to TRUE so existing exams keep counting; uncheck practice ones.
alter table exams
  add column if not exists counts_toward_graduation boolean not null default true;

-- 2) One issued diploma + letter per student per course.
create table if not exists diplomas (
    id                  uuid primary key default gen_random_uuid(),
    student_id          uuid not null references profiles(id) on delete cascade,
    course_id           uuid not null references courses(id) on delete cascade,
    gpa                 integer,
    final_grade         text,
    remark              text,
    recommendation_text text not null,
    diploma_path        text,
    letter_path         text,
    approved_by         uuid references profiles(id),
    issued_at           timestamptz not null default now(),
    created_at          timestamptz not null default now(),
    unique (student_id, course_id)
);

create index if not exists idx_diplomas_student on diplomas(student_id);

-- 3) Row-level security: staff manage everything; a student may read their own.
--    (The backend uses the service key and bypasses RLS; these policies guard
--     any direct access from the browser via supabase-js.)
alter table diplomas enable row level security;

drop policy if exists diplomas_staff_all on diplomas;
create policy diplomas_staff_all on diplomas
    for all using (is_staff()) with check (is_staff());

drop policy if exists diplomas_student_read on diplomas;
create policy diplomas_student_read on diplomas
    for select using (auth.uid() = student_id);

-- 4) Private storage bucket for the generated PDFs (downloads use signed URLs).
insert into storage.buckets (id, name, public)
values ('diplomas', 'diplomas', false)
on conflict (id) do nothing;

-- No public storage policies: files are private and only ever reached through
-- short-lived signed URLs minted by the backend (service key).
