-- ════════════════════════════════════════════════════════════
--  STAFF JOB TITLE / ROLE — a free-text label each staff member sets on
--  their own profile (e.g. "Biology & Physiology Teacher", "Technology
--  & Support"). Shown to students under the staff member's name in the
--  "Your Teaching & Supporting Staff" roster, so it's clear who does what.
--
--  Distinct from `title` (the Mr/Mrs salutation) and `role`
--  (student/admin/superadmin permission level).
--
--  Safe to re-run. Run in the Supabase SQL editor.
-- ════════════════════════════════════════════════════════════

alter table profiles add column if not exists job_title text;

-- profiles uses column-level UPDATE grants, so the new column needs its own
-- grant for staff to save it from their profile page. (No-op if the table
-- already has a table-wide update grant.)
grant update (job_title) on profiles to authenticated;
