-- ════════════════════════════════════════════════════════════
--  Only the staff member who wrote a reply (or a superadmin) may edit
--  or delete it afterward — fixes a real incident where an admin
--  replied in the wrong thread and had no way to undo it. Reading and
--  sending replies stays staff-wide; "mark a student's reply as read"
--  also stays staff-wide (any staff member may clear that, it's not
--  an edit of the reply's own content). Run once in the SQL editor.
-- ════════════════════════════════════════════════════════════

alter table student_note_replies add column if not exists edited_at timestamptz;

drop policy if exists snr_staff_all on student_note_replies;

create policy snr_staff_select on student_note_replies for select using (is_staff());
create policy snr_staff_insert on student_note_replies for insert with check (is_staff());

-- Any staff member may flip read_by_staff on a STUDENT's reply (marking it seen).
create policy snr_staff_mark_read on student_note_replies for update using (
    is_staff() and author_role = 'student'
) with check (
    is_staff() and author_role = 'student'
);

-- Only the author of a STAFF reply (or a superadmin) may edit or delete it.
create policy snr_staff_edit_own on student_note_replies for update using (
    is_staff() and author_role = 'staff' and (author_id = auth.uid() or is_superadmin())
) with check (
    is_staff() and author_role = 'staff' and (author_id = auth.uid() or is_superadmin())
);
create policy snr_staff_delete_own on student_note_replies for delete using (
    is_staff() and author_role = 'staff' and (author_id = auth.uid() or is_superadmin())
);
