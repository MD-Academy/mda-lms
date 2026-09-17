-- ════════════════════════════════════════════════════════════
--  FIX — quiz_attempts.score CHECK constraint rejects valid scores.
--  Backend stores score as a 0-100 percentage (main.py: score =
--  round(correct/total*100), and "passed" is later read back as
--  score >= 100). The live "quiz_attempts_score_check" constraint
--  was apparently defined for a different scale (e.g. raw correct
--  count), so any partial score like 90 fails the insert with
--  Postgres error 23514 and the student's quiz submission is lost.
--  Run once in the Supabase SQL editor.
-- ════════════════════════════════════════════════════════════

alter table quiz_attempts
    drop constraint if exists quiz_attempts_score_check;

alter table quiz_attempts
    add constraint quiz_attempts_score_check
    check (score is null or (score >= 0 and score <= 100));
