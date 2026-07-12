-- ════════════════════════════════════════════════════════════
--  MEETING LINKS — live Zoom class join links (NOT recordings).
--  A teacher/admin adds a link for a course; students enrolled in
--  that course see it (read-only) on the Zoom Recordings page and
--  can open it in a new tab or copy it. Run once in the SQL editor.
-- ════════════════════════════════════════════════════════════

create table if not exists meeting_links (
    id          uuid primary key default gen_random_uuid(),
    course_id   uuid not null references courses(id) on delete cascade,
    title       text not null,          -- class / purpose, e.g. "Biology — Weekly Live Class"
    host_name   text not null,          -- who created / hosts it, e.g. "Dr. Levin"
    url         text not null,          -- the Zoom join link
    is_visible  boolean not null default true,
    order_index int,
    created_at  timestamptz not null default now()
);
create index if not exists idx_meeting_links_course on meeting_links(course_id);

grant select, insert, update, delete on table meeting_links to authenticated;
grant all on table meeting_links to service_role;

alter table meeting_links enable row level security;

-- Staff manage everything.
drop policy if exists meeting_links_staff_all on meeting_links;
create policy meeting_links_staff_all on meeting_links
    for all using (is_staff()) with check (is_staff());

-- A student reads a VISIBLE link only for a course they're enrolled in
-- (course visible + not expired). Read-only — no insert/update/delete.
drop policy if exists meeting_links_student_read on meeting_links;
create policy meeting_links_student_read on meeting_links
    for select using (
        is_visible = true
        and exists (
            select 1
              from course_enrollments ce
              join courses c on c.id = meeting_links.course_id
             where ce.course_id = meeting_links.course_id
               and ce.student_id = auth.uid()
               and c.is_visible = true
               and (c.expires_at is null or c.expires_at >= current_date)
        )
    );
