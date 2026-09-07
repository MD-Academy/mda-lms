-- ════════════════════════════════════════════════════════════
--  READING PROGRESS — remembers the page a student was on in a
--  document opened in the read-only reader (viewer.html), so
--  re-opening the same file resumes right where they left off.
--
--  Keyed by (user_id, storage_path) — one row per student per file.
--  Covers booklets, subject presentations and exam PDFs alike, since
--  they all share the same reader.
--
--  Safe to re-run. Run in the Supabase SQL editor.
-- ════════════════════════════════════════════════════════════

create table if not exists reading_progress (
    id           uuid primary key default gen_random_uuid(),
    user_id      uuid not null references profiles(id) on delete cascade,
    storage_path text not null,          -- the file's storage path, same key the reader is opened with
    page         int not null default 1,
    updated_at   timestamptz not null default now(),
    unique (user_id, storage_path)
);

create index if not exists idx_reading_progress_user on reading_progress(user_id);

grant select, insert, update on reading_progress to authenticated;
grant all on reading_progress to service_role;

alter table reading_progress enable row level security;

-- A user reads and writes only their OWN progress rows.
drop policy if exists rp_own_select on reading_progress;
create policy rp_own_select on reading_progress for select using (user_id = auth.uid());

drop policy if exists rp_own_insert on reading_progress;
create policy rp_own_insert on reading_progress for insert with check (user_id = auth.uid());

drop policy if exists rp_own_update on reading_progress;
create policy rp_own_update on reading_progress for update using (user_id = auth.uid()) with check (user_id = auth.uid());
