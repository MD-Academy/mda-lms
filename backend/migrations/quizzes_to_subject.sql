-- ════════════════════════════════════════════════════════════
--  QUIZZES → SUBJECT (rooms) instead of LESSONS.
--  Quizzes now attach directly to a subject and carry their own title.
--  A subject can have several quizzes; each is still 10 questions,
--  all-correct-to-pass. Lessons are being retired from the UI.
--  Run once in the Supabase SQL editor.
-- ════════════════════════════════════════════════════════════

-- 1) New columns: parent subject + own title.
alter table quizzes add column if not exists room_id uuid references rooms(id) on delete cascade;
alter table quizzes add column if not exists title   text;

-- 2) Backfill existing quizzes from their lesson (room + a sensible title).
update quizzes q
   set room_id = l.room_id
  from lessons l
 where q.lesson_id = l.id
   and q.room_id is null;

update quizzes q
   set title = coalesce(nullif(q.title, ''), l.title, 'Quiz')
  from lessons l
 where q.lesson_id = l.id
   and (q.title is null or q.title = '');

-- Any quiz still without a title gets a default.
update quizzes set title = 'Quiz' where title is null or title = '';

-- 3) lesson_id is no longer required (new quizzes won't set it).
alter table quizzes alter column lesson_id drop not null;

create index if not exists idx_quizzes_room on quizzes(room_id);

-- 4) Row-level security.
--    These are ADDITIVE policies (new names) so they don't disturb any
--    existing lesson-based policy. Permissive policies are OR'd, so old
--    lesson-attached quizzes keep working and new room-attached ones work too.

-- Staff can do everything (needed to insert quizzes with room_id / no lesson).
drop policy if exists quizzes_staff_all_room on quizzes;
create policy quizzes_staff_all_room on quizzes
    for all using (is_staff()) with check (is_staff());

-- A student may read a VISIBLE quiz for a VISIBLE subject they're enrolled in
-- through a visible, non-expired course. Mirrors the backend access check.
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
        )
    );
