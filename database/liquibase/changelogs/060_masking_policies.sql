-- liquibase formatted sql

-- PII masking (ADR-003): clear text for PII_READER, a SHA-256 hash for TRANSFORMER
-- (dbt can deduplicate customers and detect trial abuse without seeing PII), and a
-- fixed mask for every other role.

-- changeset streampulse:masking-policy-pii-string
create masking policy if not exists ${db}.governance.pii_string
as (val varchar) returns varchar ->  -- noqa: LT01
case
    when is_role_in_session('PII_READER_${env}') then val
    when is_role_in_session('TRANSFORMER_${env}') then sha2(lower(trim(val)), 256)
    else '***MASKED***'
end
comment = 'Masks names and email addresses';
-- rollback drop masking policy if exists ${db}.governance.pii_string;

-- changeset streampulse:mask-customers-pii
alter table ${db}.raw.customers modify column first_name
set masking policy ${db}.governance.pii_string;
alter table ${db}.raw.customers modify column last_name
set masking policy ${db}.governance.pii_string;
alter table ${db}.raw.customers modify column email
set masking policy ${db}.governance.pii_string;
-- rollback alter table ${db}.raw.customers modify column email unset masking policy;
-- rollback alter table ${db}.raw.customers modify column last_name unset masking policy;
-- rollback alter table ${db}.raw.customers modify column first_name unset masking policy;

-- changeset streampulse:masking-policy-pii-email
-- comment: TRANSFORMER gets a hash of the normalized email (lowercase, +tag removed) so dbt can detect repeat trials (ADR-002).
create masking policy if not exists ${db}.governance.pii_email
as (val varchar) returns varchar ->  -- noqa: LT01
case
    when is_role_in_session('PII_READER_${env}') then val
    when is_role_in_session('TRANSFORMER_${env}')
        then sha2(regexp_replace(lower(trim(val)), '[+][^@]*@', '@'), 256)
    else '***MASKED***'
end
comment = 'Masks email addresses; hashes the normalized address for dbt';
-- rollback drop masking policy if exists ${db}.governance.pii_email;

-- changeset streampulse:mask-customers-email-normalized
alter table ${db}.raw.customers modify column email
set masking policy ${db}.governance.pii_email force;
-- rollback alter table ${db}.raw.customers modify column email set masking policy ${db}.governance.pii_string force;
