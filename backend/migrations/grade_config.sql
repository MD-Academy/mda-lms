-- ════════════════════════════════════════════════════════════
--  GLOBAL GRADE CONFIG — quizzes weight + teacher bonus cap.
--  Exam weights (exams.weight_percent) and oral weights
--  (oral_presentations.weight_percent) already exist and are set
--  per course in the Gradebook's "Manage grading" (super-admin).
--  These two are global (change once, apply everywhere). app_settings
--  already has RLS: signed-in read, staff write. Run once.
-- ════════════════════════════════════════════════════════════

insert into app_settings (key, value) values ('grade_quizzes_weight', '10')
    on conflict (key) do nothing;
insert into app_settings (key, value) values ('grade_bonus_cap', '10')
    on conflict (key) do nothing;
