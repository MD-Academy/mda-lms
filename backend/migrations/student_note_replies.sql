-- ════════════════════════════════════════════════════════════
--  FEEDBACK REPLIES — a student can reply to a piece of feedback a
--  teacher wrote for them, and the teacher can reply back. It threads
--  onto the original feedback entry, so both sides see the whole
--  conversation against the note it belongs to.
--
--  Safe to re-run. Run in the Supabase SQL editor.
-- ════════════════════════════════════════════════════════════

create table if not exists student_note_replies (
    id          uuid primary key default gen_random_uuid(),
    note_id     uuid not null references student_notes(id) on delete cascade,
    author_role text not null check (author_role in ('student', 'staff')),
    author_id   uuid,
    author_name text,                                  -- snapshot (students can't read staff profiles)
    body        text not null,
    created_at  timestamptz not null default now(),
    read_by_staff boolean not null default false       -- a student reply starts unread for staff
);

create index if not exists idx_note_replies_note on student_note_replies(note_id, created_at);
create index if not exists idx_note_replies_unread on student_note_replies(read_by_staff) where author_role = 'student';

grant select, insert, update, delete on student_note_replies to authenticated;
grant all on student_note_replies to service_role;

alter table student_note_replies enable row level security;

-- Staff read and manage every reply.
drop policy if exists snr_staff_all on student_note_replies;
create policy snr_staff_all on student_note_replies for all using (is_staff()) with check (is_staff());

-- A student reads the thread on their OWN, shared feedback entries.
drop policy if exists snr_student_read on student_note_replies;
create policy snr_student_read on student_note_replies for select using (
    exists (
        select 1 from student_notes n
         where n.id = student_note_replies.note_id
           and n.student_id = auth.uid()
           and n.visible_to_student = true
    )
);

-- A student may post ONLY their own reply, and only on their own shared feedback.
drop policy if exists snr_student_write on student_note_replies;
create policy snr_student_write on student_note_replies for insert with check (
    author_role = 'student'
    and author_id = auth.uid()
    and exists (
        select 1 from student_notes n
         where n.id = student_note_replies.note_id
           and n.student_id = auth.uid()
           and n.visible_to_student = true
    )
);

-- ── Bell notifications ──
-- Let BOTH sides track a reply as read on their own bell. notification_reads is
-- keyed by the viewer (its student_id column is really "who saw it"), and staff
-- can manage their own rows too, so the same table serves student and teacher.
alter table notification_reads drop constraint if exists notification_reads_kind_check;
alter table notification_reads add constraint notification_reads_kind_check
    check (kind in ('announcement', 'schedule', 'feedback', 'reply'));
