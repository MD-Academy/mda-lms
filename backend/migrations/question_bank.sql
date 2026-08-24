-- ════════════════════════════════════════════════════════════
--  QUESTION BANK — a reusable pool of multiple-choice questions a
--  super-admin imports (e.g. from a Moodle XML export) and then picks
--  from when building quizzes and exams. Same shape as quiz_questions /
--  exam_questions so selected questions copy straight in.
--
--  Written by the backend importer (service role). Staff read; only a
--  super-admin manages it. Run once in the Supabase SQL editor.
-- ════════════════════════════════════════════════════════════

create table if not exists question_bank (
    id                   uuid primary key default gen_random_uuid(),
    category             text,                    -- source category (for grouping/filtering)
    question_text        text not null,
    options_json         jsonb not null,          -- array of option strings
    correct_answer_index int  not null,           -- 0-based index into options_json
    source               text default 'moodle',
    created_at           timestamptz not null default now()
);
create index if not exists idx_qbank_category on question_bank(category);
create index if not exists idx_qbank_created  on question_bank(created_at desc);

grant select, insert, update, delete on question_bank to authenticated;
grant all on question_bank to service_role;

alter table question_bank enable row level security;

-- Any staff member can read the bank (so they can add questions when building a quiz/exam);
-- only a super-admin can add/import/edit/delete bank entries.
drop policy if exists qbank_staff_read on question_bank;
create policy qbank_staff_read on question_bank for select using (is_staff());

drop policy if exists qbank_super_write on question_bank;
create policy qbank_super_write on question_bank for all using (is_superadmin()) with check (is_superadmin());
