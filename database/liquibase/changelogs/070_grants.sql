-- liquibase formatted sql

-- changeset streampulse:grants-raw-read
grant usage on database ${db} to database role ${db}.raw_read;
grant usage on schema ${db}.raw to database role ${db}.raw_read;
grant select on all tables in schema ${db}.raw to database role ${db}.raw_read;
grant select on future tables in schema ${db}.raw to database role ${db}.raw_read;
-- rollback revoke select on future tables in schema ${db}.raw from database role ${db}.raw_read;
-- rollback revoke select on all tables in schema ${db}.raw from database role ${db}.raw_read;
-- rollback revoke usage on schema ${db}.raw from database role ${db}.raw_read;
-- rollback revoke usage on database ${db} from database role ${db}.raw_read;

-- changeset streampulse:grants-raw-write
grant usage on database ${db} to database role ${db}.raw_write;
grant usage on schema ${db}.raw to database role ${db}.raw_write;
grant insert on all tables in schema ${db}.raw to database role ${db}.raw_write;
grant insert on future tables in schema ${db}.raw to database role ${db}.raw_write;
grant read, write on stage ${db}.raw.landing to database role ${db}.raw_write;
grant usage on file format ${db}.raw.parquet_format to database role ${db}.raw_write;
-- rollback revoke usage on file format ${db}.raw.parquet_format from database role ${db}.raw_write;
-- rollback revoke read, write on stage ${db}.raw.landing from database role ${db}.raw_write;
-- rollback revoke insert on future tables in schema ${db}.raw from database role ${db}.raw_write;
-- rollback revoke insert on all tables in schema ${db}.raw from database role ${db}.raw_write;
-- rollback revoke usage on schema ${db}.raw from database role ${db}.raw_write;
-- rollback revoke usage on database ${db} from database role ${db}.raw_write;

-- changeset streampulse:grants-functional-roles
grant database role ${db}.raw_write to role loader_${env};
grant database role ${db}.raw_read to role transformer_${env};
grant database role ${db}.raw_read to role ai_readonly_${env};
grant database role ${db}.raw_read to role pii_reader_${env};
-- rollback revoke database role ${db}.raw_read from role pii_reader_${env};
-- rollback revoke database role ${db}.raw_read from role ai_readonly_${env};
-- rollback revoke database role ${db}.raw_read from role transformer_${env};
-- rollback revoke database role ${db}.raw_write from role loader_${env};

-- changeset streampulse:grants-warehouses
grant usage on warehouse wh_load_${env} to role loader_${env};
grant usage on warehouse wh_transform_${env} to role transformer_${env};
grant usage on warehouse wh_report_${env} to role reporter_${env};
grant usage on warehouse wh_report_${env} to role ai_readonly_${env};
grant usage on warehouse wh_report_${env} to role pii_reader_${env};
-- rollback revoke usage on warehouse wh_report_${env} from role pii_reader_${env};
-- rollback revoke usage on warehouse wh_report_${env} from role ai_readonly_${env};
-- rollback revoke usage on warehouse wh_report_${env} from role reporter_${env};
-- rollback revoke usage on warehouse wh_transform_${env} from role transformer_${env};
-- rollback revoke usage on warehouse wh_load_${env} from role loader_${env};
