-- liquibase formatted sql

-- Raw tables mirror the generator's Parquet files (data_generator/README.md) and are
-- loaded with COPY ... MATCH_BY_COLUMN_NAME. Every table ends with load metadata:
-- _file_name (stage path, includes the load date), _file_row_number, _loaded_at.

-- changeset streampulse:raw-markets
create table if not exists ${db}.raw.markets (
    market_code varchar,
    market_name varchar,
    currency_code varchar,
    _file_name varchar,
    _file_row_number number(19, 0),
    _loaded_at timestamp_ltz
);
-- rollback drop table if exists ${db}.raw.markets;

-- changeset streampulse:raw-currencies
create table if not exists ${db}.raw.currencies (
    currency_code varchar,
    currency_name varchar,
    _file_name varchar,
    _file_row_number number(19, 0),
    _loaded_at timestamp_ltz
);
-- rollback drop table if exists ${db}.raw.currencies;

-- changeset streampulse:raw-plans
create table if not exists ${db}.raw.plans (
    plan_id varchar,
    plan_name varchar,
    tier varchar,
    tier_rank number(3, 0),
    billing_period varchar,
    billing_months number(3, 0),
    _file_name varchar,
    _file_row_number number(19, 0),
    _loaded_at timestamp_ltz
);
-- rollback drop table if exists ${db}.raw.plans;

-- changeset streampulse:raw-plan-prices
create table if not exists ${db}.raw.plan_prices (
    price_id number(10, 0),
    market_code varchar,
    plan_id varchar,
    currency_code varchar,
    price number(12, 2),
    valid_from date,
    valid_to date,
    _file_name varchar,
    _file_row_number number(19, 0),
    _loaded_at timestamp_ltz
);
-- rollback drop table if exists ${db}.raw.plan_prices;

-- changeset streampulse:raw-content-catalog
create table if not exists ${db}.raw.content_catalog (
    title_id number(10, 0),
    title_name varchar,
    genre varchar,
    content_type varchar,
    runtime_minutes number(5, 0),
    release_year number(4, 0),
    added_date date,
    _file_name varchar,
    _file_row_number number(19, 0),
    _loaded_at timestamp_ltz
);
-- rollback drop table if exists ${db}.raw.content_catalog;

-- changeset streampulse:raw-campaigns
create table if not exists ${db}.raw.campaigns (
    campaign_id number(10, 0),
    campaign_name varchar,
    market_code varchar,
    channel varchar,
    start_date date,
    end_date date,
    _file_name varchar,
    _file_row_number number(19, 0),
    _loaded_at timestamp_ltz
);
-- rollback drop table if exists ${db}.raw.campaigns;

-- changeset streampulse:raw-fx-rates
create table if not exists ${db}.raw.fx_rates (
    rate_date date,
    currency_code varchar,
    units_per_eur number(12, 4),
    _file_name varchar,
    _file_row_number number(19, 0),
    _loaded_at timestamp_ltz
);
-- rollback drop table if exists ${db}.raw.fx_rates;

-- changeset streampulse:raw-campaign-spend
create table if not exists ${db}.raw.campaign_spend (
    spend_date date,
    campaign_id number(10, 0),
    currency_code varchar,
    amount number(12, 2),
    _file_name varchar,
    _file_row_number number(19, 0),
    _loaded_at timestamp_ltz
);
-- rollback drop table if exists ${db}.raw.campaign_spend;

-- changeset streampulse:raw-customers
create table if not exists ${db}.raw.customers (
    customer_id number(19, 0),
    first_name varchar,
    last_name varchar,
    email varchar,
    market_code varchar,
    created_at timestamp_ntz,
    _file_name varchar,
    _file_row_number number(19, 0),
    _loaded_at timestamp_ltz
);
-- rollback drop table if exists ${db}.raw.customers;

-- changeset streampulse:raw-acquisition-attribution
create table if not exists ${db}.raw.acquisition_attribution (
    customer_id number(19, 0),
    channel varchar,
    campaign_id number(10, 0),
    attributed_at timestamp_ntz,
    _file_name varchar,
    _file_row_number number(19, 0),
    _loaded_at timestamp_ltz
);
-- rollback drop table if exists ${db}.raw.acquisition_attribution;

-- changeset streampulse:raw-subscriptions
create table if not exists ${db}.raw.subscriptions (
    subscription_id number(19, 0),
    customer_id number(19, 0),
    market_code varchar,
    plan_id varchar,
    created_at timestamp_ntz,
    is_trial boolean,
    is_reactivation boolean,
    _file_name varchar,
    _file_row_number number(19, 0),
    _loaded_at timestamp_ltz
);
-- rollback drop table if exists ${db}.raw.subscriptions;

-- changeset streampulse:raw-subscription-events
create table if not exists ${db}.raw.subscription_events (
    event_id number(19, 0),
    subscription_id number(19, 0),
    customer_id number(19, 0),
    event_type varchar,
    event_at timestamp_ntz,
    plan_id varchar,
    previous_plan_id varchar,
    cancellation_type varchar,
    effective_date date,
    _file_name varchar,
    _file_row_number number(19, 0),
    _loaded_at timestamp_ltz
);
-- rollback drop table if exists ${db}.raw.subscription_events;

-- changeset streampulse:raw-payments
create table if not exists ${db}.raw.payments (
    payment_id number(19, 0),
    subscription_id number(19, 0),
    customer_id number(19, 0),
    plan_id varchar,
    billing_period_start date,
    attempt_number number(3, 0),
    attempted_at timestamp_ntz,
    amount number(12, 2),
    currency_code varchar,
    status varchar,
    failure_reason varchar,
    _file_name varchar,
    _file_row_number number(19, 0),
    _loaded_at timestamp_ltz
);
-- rollback drop table if exists ${db}.raw.payments;

-- changeset streampulse:raw-viewing-sessions
create table if not exists ${db}.raw.viewing_sessions (
    session_id number(19, 0),
    customer_id number(19, 0),
    title_id number(10, 0),
    started_at timestamp_ntz,
    watch_minutes number(5, 0),
    device varchar,
    _file_name varchar,
    _file_row_number number(19, 0),
    _loaded_at timestamp_ltz
);
-- rollback drop table if exists ${db}.raw.viewing_sessions;

-- changeset streampulse:raw-viewing-sessions-app-v6
-- comment: Source schema change on 2026-01-01 (device_type and app_version replace device).
alter table ${db}.raw.viewing_sessions add column if not exists device_type varchar;
alter table ${db}.raw.viewing_sessions add column if not exists app_version varchar;
-- rollback alter table ${db}.raw.viewing_sessions drop column app_version;
-- rollback alter table ${db}.raw.viewing_sessions drop column device_type;
