-- Create extensions needed for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search indexes
CREATE EXTENSION IF NOT EXISTS "btree_gin"; -- For composite GIN indexes

-- Set timezone
SET timezone = 'UTC';
