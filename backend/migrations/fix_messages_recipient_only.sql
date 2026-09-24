-- ════════════════════════════════════════════════════════════
--  MESSAGES PRIVACY — a student's message to a specific staff member
--  (student_notes.initiated_by = 'student') should only be visible to
--  that staff member, not to every superadmin. Ordinary teacher-authored
--  feedback (initiated_by = 'staff'/null) stays visible to all staff,
--  unchanged — that's a shared academic record, not a private inbox.
--
--  One staff member ("the messages owner", set below) keeps full
--  oversight and is the target overdue messages escalate to. Run once
--  in the Supabase SQL editor.
-- ════════════════════════════════════════════════════════════

-- Who is the messages owner ("super-super admin"). Change the email below
-- to re-point this at a different account later; nothing else needs to change.
insert into app_settings (key, value)
values ('messages_owner_id', (select id::text from profiles where email = 'diego@medicaldoctor-studies.com'))
on conflict (key) do update set value = excluded.value;

create or replace function is_messages_owner()
returns boolean language sql security definer stable as $$
    select exists (
        select 1 from app_settings
        where key = 'messages_owner_id' and value = auth.uid()::text
    );
$$;

-- ── student_notes ──
drop policy if exists sn_staff_all on student_notes;

create policy sn_staff_feedback on student_notes for all
    using (is_staff() and coalesce(initiated_by, 'staff') <> 'student')
    with check (is_staff() and coalesce(initiated_by, 'staff') <> 'student');

create policy sn_staff_messages on student_notes for all
    using (is_staff() and initiated_by = 'student' and (staff_id = auth.uid() or is_messages_owner()))
    with check (is_staff() and initiated_by = 'student' and (staff_id = auth.uid() or is_messages_owner()));

-- ── student_note_replies ──
drop policy if exists snr_staff_all on student_note_replies;

create policy snr_staff_feedback on student_note_replies for all
    using (
        is_staff() and exists (
            select 1 from student_notes n
            where n.id = student_note_replies.note_id and coalesce(n.initiated_by, 'staff') <> 'student'
        )
    )
    with check (
        is_staff() and exists (
            select 1 from student_notes n
            where n.id = student_note_replies.note_id and coalesce(n.initiated_by, 'staff') <> 'student'
        )
    );

create policy snr_staff_messages on student_note_replies for all
    using (
        is_staff() and exists (
            select 1 from student_notes n
            where n.id = student_note_replies.note_id
              and n.initiated_by = 'student'
              and (n.staff_id = auth.uid() or is_messages_owner())
        )
    )
    with check (
        is_staff() and exists (
            select 1 from student_notes n
            where n.id = student_note_replies.note_id
              and n.initiated_by = 'student'
              and (n.staff_id = auth.uid() or is_messages_owner())
        )
    );
