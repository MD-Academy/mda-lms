-- ════════════════════════════════════════════════════════════
--  STAFF PROFILE — a light "about me" for each staff member: a short
--  bio paragraph, their specialty, and their education. Shown to
--  students and to other admins alongside the photo (avatar_url) and
--  role (job_title) that already exist.
--
--  Safe to re-run. Run in the Supabase SQL editor.
-- ════════════════════════════════════════════════════════════

alter table profiles add column if not exists specialty  text;
alter table profiles add column if not exists bio        text;
alter table profiles add column if not exists education  text;

-- profiles uses column-level UPDATE grants, so staff editing their own
-- profile need these columns granted explicitly. (No-op if a table-wide
-- update grant is already in place.)
grant update (specialty, bio, education) on profiles to authenticated;
