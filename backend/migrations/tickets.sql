-- ════════════════════════════════════════════════════════════
--  SUPPORT TICKETS — students report problems / suggestions,
--  staff respond and set status. Run once in the SQL editor.
-- ════════════════════════════════════════════════════════════

-- 1) Tickets. status: open | in_progress | completed
create table if not exists tickets (
    id              uuid primary key default gen_random_uuid(),
    student_id      uuid not null references profiles(id) on delete cascade,
    title           text not null,
    status          text not null default 'open'
                      check (status in ('open', 'in_progress', 'completed')),
    screenshot_path text,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now()
);
create index if not exists idx_tickets_student on tickets(student_id);
create index if not exists idx_tickets_status  on tickets(status);
create index if not exists idx_tickets_updated on tickets(updated_at desc);

-- 2) Thread messages (the opening description is the first message).
create table if not exists ticket_messages (
    id          uuid primary key default gen_random_uuid(),
    ticket_id   uuid not null references tickets(id) on delete cascade,
    author_id   uuid references profiles(id) on delete set null,
    author_role text not null check (author_role in ('student', 'staff')),
    body        text not null,
    created_at  timestamptz not null default now()
);
create index if not exists idx_ticket_messages_ticket on ticket_messages(ticket_id, created_at);

-- 3) RLS. Writes go through the backend (service key, bypasses RLS); these
--    policies guard the direct reads the portals do via supabase-js.
alter table tickets enable row level security;
alter table ticket_messages enable row level security;

drop policy if exists tickets_staff_all on tickets;
create policy tickets_staff_all on tickets
    for all using (is_staff()) with check (is_staff());

drop policy if exists tickets_student_own on tickets;
create policy tickets_student_own on tickets
    for select using (auth.uid() = student_id);

drop policy if exists tmsg_staff_all on ticket_messages;
create policy tmsg_staff_all on ticket_messages
    for all using (is_staff()) with check (is_staff());

drop policy if exists tmsg_student_own on ticket_messages;
create policy tmsg_student_own on ticket_messages
    for select using (
        exists (select 1 from tickets t
                where t.id = ticket_messages.ticket_id
                  and t.student_id = auth.uid())
    );

-- 4) Public bucket for screenshots (JPG/PNG/JPEG, capped at 500KB in the UI).
insert into storage.buckets (id, name, public)
values ('ticket-uploads', 'ticket-uploads', true)
on conflict (id) do nothing;

-- Let signed-in users upload to their own folder; everyone can read (public bucket).
drop policy if exists ticket_uploads_insert on storage.objects;
create policy ticket_uploads_insert on storage.objects
    for insert to authenticated
    with check (bucket_id = 'ticket-uploads');

drop policy if exists ticket_uploads_read on storage.objects;
create policy ticket_uploads_read on storage.objects
    for select using (bucket_id = 'ticket-uploads');
