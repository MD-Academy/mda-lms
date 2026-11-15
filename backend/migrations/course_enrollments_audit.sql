-- ════════════════════════════════════════════════════════════
--  Permanent audit trail for course_enrollments — every insert, update
--  and delete is logged here automatically by a DB trigger, regardless
--  of which button or code path caused it (app bug, misclick, future
--  feature, even a manual SQL edit). Nothing can erase a row from here
--  except a superadmin with direct DB access — no app role is granted
--  insert/update/delete on this table, so it can't be edited through
--  the app, only read. Run once in the SQL editor.
-- ════════════════════════════════════════════════════════════

create table if not exists course_enrollments_audit (
    id          uuid primary key default gen_random_uuid(),
    op          text not null,                 -- 'INSERT' | 'UPDATE' | 'DELETE'
    changed_at  timestamptz not null default now(),
    changed_by  uuid,                           -- auth.uid() of whoever made the change, if known
    course_id   uuid,
    student_id  uuid,
    row_data    jsonb not null                  -- full snapshot (OLD for delete, NEW for insert, both for update)
);
create index if not exists idx_cea_student on course_enrollments_audit(student_id, changed_at desc);
create index if not exists idx_cea_course on course_enrollments_audit(course_id, changed_at desc);

create or replace function _log_course_enrollment_change() returns trigger
language plpgsql security definer as $$
begin
    if (tg_op = 'DELETE') then
        insert into course_enrollments_audit (op, changed_by, course_id, student_id, row_data)
        values ('DELETE', auth.uid(), old.course_id, old.student_id, to_jsonb(old));
        return old;
    elsif (tg_op = 'UPDATE') then
        insert into course_enrollments_audit (op, changed_by, course_id, student_id, row_data)
        values ('UPDATE', auth.uid(), new.course_id, new.student_id, jsonb_build_object('old', to_jsonb(old), 'new', to_jsonb(new)));
        return new;
    else
        insert into course_enrollments_audit (op, changed_by, course_id, student_id, row_data)
        values ('INSERT', auth.uid(), new.course_id, new.student_id, to_jsonb(new));
        return new;
    end if;
end;
$$;

drop trigger if exists trg_course_enrollments_audit on course_enrollments;
create trigger trg_course_enrollments_audit
after insert or update or delete on course_enrollments
for each row execute function _log_course_enrollment_change();

grant select on course_enrollments_audit to authenticated;
grant all on course_enrollments_audit to service_role;

alter table course_enrollments_audit enable row level security;

-- Staff may only ever READ this table. No insert/update/delete policy is
-- granted to anyone — the security-definer trigger writes it regardless of
-- the caller's own privileges, and nothing else can touch it through the app.
drop policy if exists cea_staff_select on course_enrollments_audit;
create policy cea_staff_select on course_enrollments_audit for select using (is_staff());
