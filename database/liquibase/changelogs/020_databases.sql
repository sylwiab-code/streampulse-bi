-- liquibase formatted sql

-- changeset streampulse:database
create database if not exists ${db}
comment = 'StreamPulse ${env} environment';
-- rollback drop database if exists ${db};

-- changeset streampulse:schema-raw
create schema if not exists ${db}.raw
comment = 'Raw data as loaded from the generator files';
-- rollback drop schema if exists ${db}.raw;

-- changeset streampulse:schema-governance
create schema if not exists ${db}.governance
comment = 'Masking policies and other governance objects';
-- rollback drop schema if exists ${db}.governance;
