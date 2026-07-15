-- ════════════════════════════════════════════════════════════
--  CONTENT-USE POLICY ACCEPTANCE — recorded once per student.
--  On first login the student must accept that content is
--  watermarked/traced and that recording & redistribution is
--  prohibited. Run once in the Supabase SQL editor.
-- ════════════════════════════════════════════════════════════

create table if not exists policy_acceptances (
    student_id   uuid primary key references profiles(id) on delete cascade,
    version      text not null default 'v1',
    accepted_at  timestamptz not null default now()
);

grant select, insert, update on policy_acceptances to authenticated;
grant all on policy_acceptances to service_role;

alter table policy_acceptances enable row level security;

drop policy if exists pa_own on policy_acceptances;
create policy pa_own on policy_acceptances
    for all using (student_id = auth.uid()) with check (student_id = auth.uid());
