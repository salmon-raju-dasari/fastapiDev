-- Fix PostgreSQL permissions for pos_inventory user
-- Run this as the postgres superuser or cloudsqladmin user

-- For GCP Cloud SQL, run these commands in order:

-- 1. Connect to the pos_inventory database
\c pos_inventory

-- 2. Grant all privileges on the database
GRANT ALL PRIVILEGES ON DATABASE pos_inventory TO pos_inventory;

-- 3. Grant usage and create on schema public
GRANT USAGE ON SCHEMA public TO pos_inventory;
GRANT CREATE ON SCHEMA public TO pos_inventory;

-- 4. Grant all privileges on all existing tables
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO pos_inventory;

-- 5. Grant all privileges on all existing sequences
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO pos_inventory;

-- 6. Grant all privileges on all existing functions
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO pos_inventory;

-- 7. Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO pos_inventory;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO pos_inventory;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON FUNCTIONS TO pos_inventory;

-- 8. Alternative: Make the user owner of the schema (RECOMMENDED for Cloud SQL)
ALTER SCHEMA public OWNER TO pos_inventory;

-- 9. Grant CONNECT privilege
GRANT CONNECT ON DATABASE pos_inventory TO pos_inventory;

-- 10. Grant TEMPORARY privilege (for temp tables)
GRANT TEMPORARY ON DATABASE pos_inventory TO pos_inventory;
