-- ════════════════════════════════════════════════════════════
--  ORAL PRESENTATIONS + WEIGHTED GRADES.
--  Written exams (auto-graded) weigh 20% each by default; oral
--  presentations (manually graded, with feedback) weigh 10% each.
--  A per-student per-course adjustment (± points) covers
--  participation/attendance. Run once in the Supabase SQL editor.
-- ════════════════════════════════════════════════════════════

-- 1) Weight on each exam (default 20%).
alter table exams add column if not exists weight_percent numeric(5,2) not null default 20;

-- 2) Oral presentation definitions (per course).
create table if not exists oral_presentations (
    id             uuid primary key default gen_random_uuid(),
    course_id      uuid not null references courses(id) on delete cascade,
    title          text not null,
    weight_percent numeric(5,2) not null default 10,
    order_index    int,
    is_visible     boolean not null default true,
    created_at     timestamptz not null default now()
);
create index if not exists idx_oral_pres_course on oral_presentations(course_id);

-- 3) Per-student oral grade + feedback paragraph.
create table if not exists oral_grades (
    id                    uuid primary key default gen_random_uuid(),
    oral_presentation_id  uuid not null references oral_presentations(id) on delete cascade,
    student_id            uuid not null references profiles(id) on delete cascade,
    score                 numeric(5,2),   -- 0..100
    feedback              text,
    graded_by             uuid,
    graded_at             timestamptz not null default now(),
    unique (oral_presentation_id, student_id)
);
create index if not exists idx_oral_grades_student on oral_grades(student_id);

-- 4) Per-student per-course adjustment (participation / attendance).
create table if not exists course_grade_adjustments (
    id          uuid primary key default gen_random_uuid(),
    course_id   uuid not null references courses(id) on delete cascade,
    student_id  uuid not null references profiles(id) on delete cascade,
    adjustment  numeric(5,2) not null default 0,
    note        text,
    updated_by  uuid,
    updated_at  timestamptz not null default now(),
    unique (course_id, student_id)
);
create index if not exists idx_cga_student on course_grade_adjustments(student_id);

grant select, insert, update, delete on oral_presentations, oral_grades, course_grade_adjustments to authenticated;
grant all on oral_presentations, oral_grades, course_grade_adjustments to service_role;

alter table oral_presentations enable row level security;
alter table oral_grades enable row level security;
alter table course_grade_adjustments enable row level security;

-- Staff manage everything.
drop policy if exists op_staff_all on oral_presentations;
create policy op_staff_all on oral_presentations for all using (is_staff()) with check (is_staff());
drop policy if exists og_staff_all on oral_grades;
create policy og_staff_all on oral_grades for all using (is_staff()) with check (is_staff());
drop policy if exists cga_staff_all on course_grade_adjustments;
create policy cga_staff_all on course_grade_adjustments for all using (is_staff()) with check (is_staff());

-- Students: read visible oral definitions for their enrolled (visible, non-expired) courses.
drop policy if exists op_student_read on oral_presentations;
create policy op_student_read on oral_presentations for select using (
    is_visible = true
    and exists (
        select 1 from course_enrollments ce
          join courses c on c.id = oral_presentations.course_id
         where ce.course_id = oral_presentations.course_id
           and ce.student_id = auth.uid()
           and c.is_visible = true
           and (c.expires_at is null or c.expires_at >= current_date)
    )
);

-- Students: read only their OWN oral grades / adjustments.
drop policy if exists og_student_own on oral_grades;
create policy og_student_own on oral_grades for select using (student_id = auth.uid());
drop policy if exists cga_student_own on course_grade_adjustments;
create policy cga_student_own on course_grade_adjustments for select using (student_id = auth.uid());
