-- Optional reference rows for HEB DSR/WSR projects.
-- Run AFTER: alembic upgrade head
-- Safe to re-run: uses project_key ON CONFLICT DO UPDATE.

INSERT INTO projects (project_key, project_name) VALUES
    ('LOC',  'LOCO'),
    ('COST', 'Cost Core Service'),
    ('GSS',  'GSS'),
    ('WNF',  'Wentforth'),
    ('PHRM', 'Pharamacy'),
    ('SUP',  'Supplier QA'),
    ('SPUR', 'SPUR'),
    ('PRC',  'Pricing')
ON CONFLICT (project_key) DO UPDATE
    SET project_name = EXCLUDED.project_name;

-- Sprint names come from Rovo per project. Examples of real sprint name formats:
--   Nacogdoches - 248
--   Q2.13FY26 Eridanus
--   Q2.14 FY26 Fornax
--
-- Sprints are created automatically on import via seed_from_rovo.py
-- (one sprint_id per unique sprint_name).
