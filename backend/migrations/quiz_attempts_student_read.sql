-- ════════════════════════════════════════════════════════════
--  Students can now read their OWN quiz_attempts rows directly (needed
--  for the new per-quiz "last attempt" status shown on the subject
--  page). Previously a student's browser never queried this table
--  directly — the score was only ever returned once, inline, from the
--  submit API response — so this read policy may not exist at all yet.
--  Safe to re-run.
-- ════════════════════════════════════════════════════════════

alter table quiz_attempts enable row level security;

drop policy if exists qa_student_own on quiz_attempts;
create policy qa_student_own on quiz_attempts
    for select using (student_id = auth.uid());
