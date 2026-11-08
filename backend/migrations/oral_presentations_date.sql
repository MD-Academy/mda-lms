-- ════════════════════════════════════════════════════════════
--  Adds a date to each oral presentation, so the new "Presentations"
--  tab can show/sort by when it happened. Everything else about
--  oral_presentations/oral_grades (weights, RLS, grading) is unchanged.
--  Run once in the Supabase SQL editor.
-- ════════════════════════════════════════════════════════════

alter table oral_presentations add column if not exists presentation_date date;
