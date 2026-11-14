-- liquibase formatted sql

-- changeset streampulse:warehouse-load
create warehouse if not exists wh_load_${env}
with warehouse_size = xsmall
auto_suspend = 60
auto_resume = true
initially_suspended = true
comment = 'Loading raw files';
-- rollback drop warehouse if exists wh_load_${env};

-- changeset streampulse:warehouse-transform
create warehouse if not exists wh_transform_${env}
with warehouse_size = xsmall
auto_suspend = 60
auto_resume = true
initially_suspended = true
comment = 'dbt transformations';
-- rollback drop warehouse if exists wh_transform_${env};

-- changeset streampulse:warehouse-report
create warehouse if not exists wh_report_${env}
with warehouse_size = xsmall
auto_suspend = 60
auto_resume = true
initially_suspended = true
comment = 'Reporting and exploratory queries';
-- rollback drop warehouse if exists wh_report_${env};
