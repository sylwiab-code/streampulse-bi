-- liquibase formatted sql

-- changeset streampulse:file-format-parquet
create file format if not exists ${db}.raw.parquet_format
    type = parquet
    comment = 'Generator output';
-- rollback drop file format if exists ${db}.raw.parquet_format;

-- changeset streampulse:stage-landing
create stage if not exists ${db}.raw.landing
    file_format = ${db}.raw.parquet_format
    comment = 'Internal stage: <table>/load_date=YYYY-MM-DD/*.parquet';
-- rollback drop stage if exists ${db}.raw.landing;
