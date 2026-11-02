-- Per-enrollment flag: does this enrollment count toward in-person attendance
-- and the weekly attendance reminder email? Defaults to true, so every existing
-- and future normal enrollment is unaffected. Only the "assign also to another
-- course" cross-enrollment flow sets this to false.
alter table course_enrollments
  add column if not exists attendance_tracked boolean not null default true;
