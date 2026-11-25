-- Separate database for pytest so test runs do not touch dev data.
-- Postgres only runs this when the data volume is created for the first time.
CREATE DATABASE forge_test;