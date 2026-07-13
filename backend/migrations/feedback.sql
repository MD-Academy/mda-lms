-- ════════════════════════════════════════════════════════════
--  STUDENT FEEDBACK & RATINGS.
--  Students rate (1–5 stars) + comment on: the course overall, each
--  teacher assigned to the course, the materials, and each Zoom
--  recording (per-lesson, prompted after watching).
--  course_teachers links staff to courses so students rate real people.
--  Feedback is ANONYMOUS to teachers — only super-admin reads it.
--  Run once in the Supabase SQL editor.
-- ════════════════════════════════════════════════════════════

-- Which staff teach a course (so students know who to rate).
create table if not exists course_teachers (
    course_id   uuid not null references courses(id) on delete cascade,
    teacher_id  uuid not null references profiles(id) on delete cascade,
    created_at  timestamptz not null default now(),
    primary key (course_id, teacher_id)
);
create index if not exists idx_course_teachers_course on course_teachers(course_id);

-- One rating per student per target.
create table if not exists feedback (
    id           uuid primary key default gen_random_uuid(),
    student_id   uuid not null references profiles(id) on delete cascade,
    course_id    uuid not null references courses(id) on delete cascade,
    target_type  text not null check (target_type in ('course','teacher','materials','recording')),
    target_id    uuid,                 -- teacher id or recording id; null for course/materials
    stars        int  not null check (stars between 1 and 5),
    comment      text,
    created_at   timestamptz not null default now(),
    updated_at   timestamptz not null default now()
);
-- Prevent duplicate ratings (null target_id → fixed sentinel so course/materials are unique per student).
create unique index if not exists uq_feedback_target on feedback
    (student_id, course_id, target_type, coalesce(target_id, '00000000-0000-0000-0000-000000000000'::uuid));
create index if not exists idx_feedback_course on feedback(course_id);
create index if not exists idx_feedback_target on feedback(target_type, target_id);

grant select on course_teachers to authenticated;
grant all on course_teachers to service_role;
grant select, insert, update, delete on feedback to authenticated;
grant all on feedback to service_role;

alter table course_teachers enable row level security;
alter table feedback enable row level security;

-- course_teachers: staff manage; students read (to know who to rate) for their enrolled courses.
drop policy if exists ct_staff_all on course_teachers;
create policy ct_staff_all on course_teachers for all using (is_staff()) with check (is_staff());
drop policy if exists ct_student_read on course_teachers;
create policy ct_student_read on course_teachers for select using (
    exists (
        select 1 from course_enrollments ce
          join courses c on c.id = course_teachers.course_id
         where ce.course_id = course_teachers.course_id
           and ce.student_id = auth.uid()
           and c.is_visible = true
           and (c.expires_at is null or c.expires_at >= current_date)
    )
);

-- feedback: a student writes/reads their OWN (and only for courses they're enrolled in).
drop policy if exists fb_student_own on feedback;
create policy fb_student_own on feedback
    for all
    using (student_id = auth.uid())
    with check (
        student_id = auth.uid()
        and exists (select 1 from course_enrollments ce where ce.course_id = feedback.course_id and ce.student_id = auth.uid())
    );

-- Super-admin (the boss) reads everyone's feedback for the report. Teachers/admins get NO read.
drop policy if exists fb_super_read on feedback;
create policy fb_super_read on feedback for select using (is_superadmin());

-- Students may see which of THEIR enrolled courses a recording belongs to, so the
-- "rate after watching" prompt can attribute the rating to a course. (Additive policy.)
drop policy if exists rc_student_read on recording_courses;
create policy rc_student_read on recording_courses for select using (
    exists (select 1 from course_enrollments ce where ce.course_id = recording_courses.course_id and ce.student_id = auth.uid())
);
