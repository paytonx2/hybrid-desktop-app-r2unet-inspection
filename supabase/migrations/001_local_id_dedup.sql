-- ============================================================
-- Migration 001 — run once in Supabase → SQL Editor → New query → Run
-- (only needed if you created the table with an older schema.sql)
-- ============================================================

-- 1) Duplicate protection.
--    The desktop app now sends its SQLite row id as local_id. If an upload
--    succeeds but the app crashes before marking the row as synced, the
--    retry is ignored instead of creating a second copy.
alter table inspections add column if not exists local_id bigint;

do $$
begin
    if not exists (
        select 1 from pg_constraint where conname = 'inspections_device_local_uniq'
    ) then
        alter table inspections
            add constraint inspections_device_local_uniq unique (device_id, local_id);
    end if;
end $$;

-- 2) OPTIONAL — fix the timestamps of rows synced before the timezone fix.
--    Older app versions sent Thai local time without a timezone, so Postgres
--    stored it as UTC (7 hours too late). Rows synced before this migration
--    have local_id = null, which is how we find them.
--    Remove the leading "--" from the next line to apply it (run it ONCE only):
-- update inspections set ts = ts - interval '7 hours' where local_id is null;
