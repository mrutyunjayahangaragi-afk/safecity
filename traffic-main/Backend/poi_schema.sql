-- ═══════════════════════════════════════════════════════════════════════════
-- SafeRoute AI — POI Schema (Parking, Hospitals, Police)
-- ═══════════════════════════════════════════════════════════════════════════

create table if not exists public.parking (
  id uuid primary key,
  city text not null,
  parking_name text not null,
  latitude double precision not null,
  longitude double precision not null,
  area text,
  capacity integer default 0,
  available_spaces integer default 0,
  occupancy_percentage double precision default 0,
  parking_type text,
  fee_per_hour integer default 0,
  safety_score double precision default 0,
  lighting_score double precision default 0,
  cctv_score double precision default 0,
  security_guard boolean default false,
  walking_distance_m integer default 0,
  ev_charging boolean default false,
  accessible_parking boolean default false,
  status text default 'Active',
  last_updated timestamptz not null default now()
);

create table if not exists public.hospitals (
  id uuid primary key,
  city text not null,
  hospital_name text not null,
  latitude double precision not null,
  longitude double precision not null,
  area text,
  hospital_type text,
  emergency boolean default false,
  trauma_center boolean default false,
  ambulance_available integer default 0,
  beds_available integer default 0,
  icu_available integer default 0,
  contact_number text,
  average_response_time_min integer default 0,
  safety_rating double precision default 0,
  occupancy_percentage double precision default 0,
  open_24x7 boolean default true,
  last_updated timestamptz not null default now()
);

create table if not exists public.police (
  id uuid primary key,
  city text not null,
  station_name text not null,
  latitude double precision not null,
  longitude double precision not null,
  area text,
  jurisdiction text,
  emergency_number text,
  women_helpdesk boolean default false,
  cyber_cell boolean default false,
  patrol_units integer default 0,
  average_response_time_min integer default 0,
  officers_available integer default 0,
  safety_rating double precision default 0,
  open_24x7 boolean default true,
  last_updated timestamptz not null default now()
);

-- Indexes for spatial queries and city filtering
create index if not exists idx_parking_city on public.parking(city);
create index if not exists idx_parking_latlon on public.parking(latitude, longitude);

create index if not exists idx_hospitals_city on public.hospitals(city);
create index if not exists idx_hospitals_latlon on public.hospitals(latitude, longitude);

create index if not exists idx_police_city on public.police(city);
create index if not exists idx_police_latlon on public.police(latitude, longitude);
