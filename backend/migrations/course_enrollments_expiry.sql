-- ════════════════════════════════════════════════════════════
--  PER-STUDENT COURSE EXPIRY — optional cutoff on a single
--  enrollment, independent of the course's own expires_at. For a
--  shared course (e.g. pre-recorded, bought independently by many
--  students) where the course itself has no end date, but one
--  student's personal access to it should still end on a given day.
--  Idempotent: safe to run even though the column/policies may
--  already exist. Run once in the Supabase SQL editor.
-- ════════════════════════════════════════════════════════════

alter table course_enrollments add column if not exists expires_at date;

-- Quizzes: add the per-enrollment check alongside the existing course-level one.
drop policy if exists quizzes_student_room_read on quizzes;
create policy quizzes_student_room_read on quizzes
    for select using (
        is_visible = true
        and exists (
            select 1
              from rooms r
             where r.id = quizzes.room_id
               and r.is_visible = true
        )
        and exists (
            select 1
              from course_subjects cs
              join course_enrollments ce on ce.course_id = cs.course_id
              join courses c            on c.id          = cs.course_id
             where cs.room_id = quizzes.room_id
               and ce.student_id = auth.uid()
               and c.is_visible = true
               and (c.expires_at is null or c.expires_at >= current_date)
               and (ce.expires_at is null or ce.expires_at >= current_date)
        )
    );

-- Oral presentation definitions: same addition.
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
           and (ce.expires_at is null or ce.expires_at >= current_date)
    )
);

-- Meeting links: same addition.
drop policy if exists meeting_links_student_read on meeting_links;
create policy meeting_links_student_read on meeting_links
    for select using (
        is_visible = true
        and exists (
            select 1
              from course_enrollments ce
              join courses c on c.id = meeting_links.course_id
             where ce.course_id = meeting_links.course_id
               and ce.student_id = auth.uid()
               and c.is_visible = true
               and (c.expires_at is null or c.expires_at >= current_date)
               and (ce.expires_at is null or ce.expires_at >= current_date)
        )
    );

-- Recordings (via recording_courses): previously had NO expiry check at all,
-- not even the course's own — adding both for the first time here.
drop policy if exists rc_student_read on recording_courses;
create policy rc_student_read on recording_courses for select using (
    exists (
        select 1 from course_enrollments ce
          join courses c on c.id = recording_courses.course_id
         where ce.course_id = recording_courses.course_id
           and ce.student_id = auth.uid()
           and (c.expires_at is null or c.expires_at >= current_date)
           and (ce.expires_at is null or ce.expires_at >= current_date)
    )
);
