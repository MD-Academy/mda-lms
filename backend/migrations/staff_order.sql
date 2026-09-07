-- ════════════════════════════════════════════════════════════
--  STAFF DISPLAY ORDER — lets the super-admin arrange the order staff
--  appear in (Staff page, and the "Your Teaching & Supporting Staff"
--  roster students see) instead of it being fixed by account creation
--  order.
--
--  Written only by the backend (service role) via
--  POST /admin/set-staff-order — no client grant needed. Anyone not
--  yet arranged (null) sorts after everyone who has been, so newly
--  created staff don't jump ahead unexpectedly.
--
--  Safe to re-run. Run in the Supabase SQL editor.
-- ════════════════════════════════════════════════════════════

alter table profiles add column if not exists staff_order integer;
