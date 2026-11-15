-- liquibase formatted sql

-- dbt schemas (ADR-002, ADR-003): created here with managed access so the deployer can
-- define future grants; dbt creates and owns the tables and views inside them.

-- changeset streampulse:schema-staging
create schema if not exists ${db}.staging
with managed access
comment = 'dbt staging models: cleaned, deduplicated source data';
-- rollback drop schema if exists ${db}.staging;

-- changeset streampulse:schema-intermediate
create schema if not exists ${db}.intermediate
with managed access
comment = 'dbt intermediate models';
-- rollback drop schema if exists ${db}.intermediate;

-- changeset streampulse:schema-marts
create schema if not exists ${db}.marts
with managed access
comment = 'dbt marts: star schema for reporting';
-- rollback drop schema if exists ${db}.marts;

-- changeset streampulse:schema-kpi
create schema if not exists ${db}.kpi
with managed access
comment = 'dbt KPI models: the source of the KPI catalog';
-- rollback drop schema if exists ${db}.kpi;

-- changeset streampulse:schema-snapshots
create schema if not exists ${db}.snapshots
with managed access
comment = 'dbt snapshots (SCD2 history)';
-- rollback drop schema if exists ${db}.snapshots;

-- changeset streampulse:database-role-analytics-write
create database role if not exists ${db}.analytics_write;
-- rollback drop database role if exists ${db}.analytics_write;

-- changeset streampulse:database-role-analytics-read
create database role if not exists ${db}.analytics_read;
-- rollback drop database role if exists ${db}.analytics_read;

-- changeset streampulse:grants-analytics-write
grant usage on database ${db} to database role ${db}.analytics_write;
grant usage, create table, create view on schema ${db}.staging
to database role ${db}.analytics_write;
grant usage, create table, create view on schema ${db}.intermediate
to database role ${db}.analytics_write;
grant usage, create table, create view on schema ${db}.marts
to database role ${db}.analytics_write;
grant usage, create table, create view on schema ${db}.kpi
to database role ${db}.analytics_write;
grant usage, create table, create view on schema ${db}.snapshots
to database role ${db}.analytics_write;
-- rollback revoke usage, create table, create view on schema ${db}.snapshots from database role ${db}.analytics_write;
-- rollback revoke usage, create table, create view on schema ${db}.kpi from database role ${db}.analytics_write;
-- rollback revoke usage, create table, create view on schema ${db}.marts from database role ${db}.analytics_write;
-- rollback revoke usage, create table, create view on schema ${db}.intermediate from database role ${db}.analytics_write;
-- rollback revoke usage, create table, create view on schema ${db}.staging from database role ${db}.analytics_write;
-- rollback revoke usage on database ${db} from database role ${db}.analytics_write;

-- changeset streampulse:grants-analytics-read
grant usage on database ${db} to database role ${db}.analytics_read;
grant usage on schema ${db}.marts to database role ${db}.analytics_read;
grant select on future tables in schema ${db}.marts
to database role ${db}.analytics_read;
grant select on future views in schema ${db}.marts
to database role ${db}.analytics_read;
grant usage on schema ${db}.kpi to database role ${db}.analytics_read;
grant select on future tables in schema ${db}.kpi
to database role ${db}.analytics_read;
grant select on future views in schema ${db}.kpi
to database role ${db}.analytics_read;
-- rollback revoke select on future views in schema ${db}.kpi from database role ${db}.analytics_read;
-- rollback revoke select on future tables in schema ${db}.kpi from database role ${db}.analytics_read;
-- rollback revoke usage on schema ${db}.kpi from database role ${db}.analytics_read;
-- rollback revoke select on future views in schema ${db}.marts from database role ${db}.analytics_read;
-- rollback revoke select on future tables in schema ${db}.marts from database role ${db}.analytics_read;
-- rollback revoke usage on schema ${db}.marts from database role ${db}.analytics_read;
-- rollback revoke usage on database ${db} from database role ${db}.analytics_read;

-- changeset streampulse:grants-analytics-functional-roles
grant database role ${db}.analytics_write to role transformer_${env};
grant database role ${db}.analytics_read to role reporter_${env};
grant database role ${db}.analytics_read to role ai_readonly_${env};
grant database role ${db}.analytics_read to role pii_reader_${env};
-- rollback revoke database role ${db}.analytics_read from role pii_reader_${env};
-- rollback revoke database role ${db}.analytics_read from role ai_readonly_${env};
-- rollback revoke database role ${db}.analytics_read from role reporter_${env};
-- rollback revoke database role ${db}.analytics_write from role transformer_${env};
