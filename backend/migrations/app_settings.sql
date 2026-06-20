-- ════════════════════════════════════════════════════════════
--  APP SETTINGS — small key/value store for office-wide settings.
--  First use: the recommended number of universities a student
--  should select (shown to students as a friendly recommendation).
--  Run once in the SQL editor.
-- ════════════════════════════════════════════════════════════

create table if not exists app_settings (
    key        text primary key,
    value      text,
    updated_at timestamptz not null default now()
);

insert into app_settings (key, value)
values ('university_target', '3')
on conflict (key) do nothing;

alter table app_settings enable row level security;

-- Anyone signed in can read settings (just a number; not sensitive).
drop policy if exists app_settings_read on app_settings;
create policy app_settings_read on app_settings
    for select using (true);

-- Only staff can change settings.
drop policy if exists app_settings_write on app_settings;
create policy app_settings_write on app_settings
    for all using (is_staff()) with check (is_staff());
