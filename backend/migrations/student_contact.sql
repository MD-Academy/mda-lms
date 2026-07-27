-- ════════════════════════════════════════════════════════════
--  MESSAGES — students can now start a conversation with a specific
--  staff member ("Contact"), not only receive feedback. We reuse the
--  existing feedback thread (student_notes + student_note_replies);
--  a note just gains a direction and the staff member it's with.
--
--    initiated_by = 'staff'   → feedback a teacher wrote (existing)
--    initiated_by = 'student' → a message a student sent a staff member
--
--    staff_id / staff_name = the staff member this thread is WITH
--    (for feedback that's the author; for a contact it's the recipient)
--
--  Safe to re-run. Run in the Supabase SQL editor.
-- ════════════════════════════════════════════════════════════

alter table student_notes add column if not exists initiated_by text not null default 'staff';
alter table student_notes add column if not exists staff_id   uuid;
alter table student_notes add column if not exists staff_name text;

-- Backfill existing feedback: the staff member is the author.
update student_notes
   set staff_id = author_id, staff_name = author_name
 where staff_id is null;

create index if not exists idx_student_notes_staff on student_notes(staff_id, created_at desc);
