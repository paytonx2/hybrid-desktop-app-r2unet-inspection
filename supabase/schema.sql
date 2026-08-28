-- ============================================================
-- R2U-NET Inspection Pro — Supabase schema
-- Run this once in: Supabase Dashboard → SQL Editor → New Query → Run
-- ============================================================

create table if not exists inspections (
    id           bigint generated always as identity primary key,
    device_id    text not null,                 -- which local machine sent this
    ts           timestamptz not null default now(),  -- when the inspection happened
    source       text,                            -- "Live Camera" / "Video/Live" / filename
    model_type   text,                            -- "defect" / "tank_screw"
    status       text check (status in ('GOOD', 'MISSING')),
    pixel_count  integer,
    conf_threshold real,
    px_threshold integer,
    created_at   timestamptz not null default now()
);

-- Helpful index for the dashboard's "latest first" queries
create index if not exists inspections_created_at_idx
    on inspections (created_at desc);

-- ============================================================
-- Row Level Security
-- We use the Supabase "anon" key from both the desktop app (insert)
-- and the web dashboard (read-only). Since this is a school project
-- with no sensitive data, we keep the policy simple and permissive.
-- For a real deployment you would scope this by device_id / auth.uid().
-- ============================================================
alter table inspections enable row level security;

create policy "anon can insert inspections"
    on inspections for insert
    to anon
    with check (true);

create policy "anon can read inspections"
    on inspections for select
    to anon
    using (true);

-- ============================================================
-- Enable Realtime on this table so the dashboard gets live updates.
-- (Also do this by hand: Supabase Dashboard → Database → Replication
--  → toggle "inspections" ON, in case this command is not permitted
--  on your plan.)
-- ============================================================
alter publication supabase_realtime add table inspections;
