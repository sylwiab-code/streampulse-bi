-- liquibase formatted sql

-- Access roles: database roles that hold privileges inside one environment.

-- changeset streampulse:database-role-raw-read
create database role if not exists ${db}.raw_read;
-- rollback drop database role if exists ${db}.raw_read;

-- changeset streampulse:database-role-raw-write
create database role if not exists ${db}.raw_write;
-- rollback drop database role if exists ${db}.raw_write;

-- changeset streampulse:role-loader
-- comment: Functional roles are account roles per environment, granted to users.
create role if not exists loader_${env} comment = 'Loads raw files (${env})';
grant role loader_${env} to role sysadmin;
-- rollback drop role if exists loader_${env};

-- changeset streampulse:role-transformer
create role if not exists transformer_${env} comment = 'Runs dbt; sees hashed PII (${env})';
grant role transformer_${env} to role sysadmin;
-- rollback drop role if exists transformer_${env};

-- changeset streampulse:role-reporter
create role if not exists reporter_${env} comment = 'Power BI and reporting (${env})';
grant role reporter_${env} to role sysadmin;
-- rollback drop role if exists reporter_${env};

-- changeset streampulse:role-ai-readonly
create role if not exists ai_readonly_${env} comment = 'AI agents; read-only, masked PII (${env})';
grant role ai_readonly_${env} to role sysadmin;
-- rollback drop role if exists ai_readonly_${env};

-- changeset streampulse:role-pii-reader
create role if not exists pii_reader_${env} comment = 'Sees PII in clear text (${env})';
grant role pii_reader_${env} to role sysadmin;
-- rollback drop role if exists pii_reader_${env};
