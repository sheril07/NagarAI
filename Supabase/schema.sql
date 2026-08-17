-- NagarAI shared complaints table.
-- Every modality (voice, text, photo) inserts a row here in the same shape.
-- severity, cluster_id, and priority_score stay null at intake time and get
-- filled in by the identify/link steps downstream.

create table complaints (
  id uuid primary key default gen_random_uuid(),
  source_modality text not null,        -- 'voice' | 'text' | 'photo'

  -- fields every intake module produces
  category text,                        -- 'pothole' | 'garbage' | 'streetlight' | 'waterlogging' | 'other'
  location_mention text,                -- landmark/street mentioned in the complaint itself
  description text,                     -- one-line clean summary
  raw_transcript text,                  -- only set for voice (english transcript)

  -- location: GPS is ground truth, geocoded_lat/lng is the fallback
  -- from geocoding location_mention when GPS wasn't available
  gps_lat double precision,
  gps_lng double precision,
  geocoded_lat double precision,
  geocoded_lng double precision,

  -- media
  audio_url text,
  image_url text,

  -- filled in later by identify + link steps, not by intake
  severity int,
  people_affected int default 1,
  cluster_id uuid,
  priority_score double precision,

  status text default 'pending',        -- 'pending' | 'in_progress' | 'resolved'
  created_at timestamptz default now()
);

create index on complaints (cluster_id);
create index on complaints (gps_lat, gps_lng);
