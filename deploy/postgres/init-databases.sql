-- Runs once on first cluster initialisation (docker-entrypoint-initdb.d).
-- Creates the application databases. `mealplan` is used by this app;
-- `keycloak` is provisioned ahead of the auth convoy. Guarded so re-runs
-- against an existing cluster are no-ops.
SELECT 'CREATE DATABASE mealplan'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'mealplan')\gexec

SELECT 'CREATE DATABASE keycloak'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'keycloak')\gexec
