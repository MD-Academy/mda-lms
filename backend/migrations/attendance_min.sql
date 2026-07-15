-- ════════════════════════════════════════════════════════════
--  ATTENDANCE MINIMUM — global threshold (%) below which a student
--  is warned (portal + weekly email). Super-admin editable on the
--  admin Attendance page. app_settings already exists. Run once.
-- ════════════════════════════════════════════════════════════

insert into app_settings (key, value) values ('attendance_min', '80')
    on conflict (key) do nothing;
