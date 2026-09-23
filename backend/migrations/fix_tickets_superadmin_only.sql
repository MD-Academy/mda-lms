-- ════════════════════════════════════════════════════════════
--  FIX — Student Tickets was readable/writable by ANY staff
--  (teachers included), so every teacher saw every student's
--  support tickets regardless of who they teach. Restrict staff
--  access to superadmins only, matching the app's "Student
--  Tickets" nav item which is now superadminOnly. Students keep
--  read access to their own tickets. Run once in the Supabase
--  SQL editor.
-- ════════════════════════════════════════════════════════════

drop policy if exists tickets_staff_all on tickets;
create policy tickets_staff_all on tickets
    for all using (is_superadmin()) with check (is_superadmin());

drop policy if exists tmsg_staff_all on ticket_messages;
create policy tmsg_staff_all on ticket_messages
    for all using (is_superadmin()) with check (is_superadmin());
