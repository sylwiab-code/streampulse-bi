-- liquibase formatted sql

-- changeset streampulse:database
create database if not exists ${db}
comment = 'StreamPulse ${env} environment';
-- rollback drop database if exists ${db};

-- changeset streampulse:schema-raw
-- comment: Managed access lets the owner define future grants without account-wide MANAGE GRANTS.
create schema if not exists ${db}.raw
with managed access
comment = 'Raw data as loaded from the generator files';
-- rollback drop schema if exists ${db}.raw;

-- changeset streampulse:schema-governance
create schema if not exists ${db}.governance
comment = 'Masking policies and other governance objects';
-- rollback drop schema if exists ${db}.governance;
