-- One-time account setup for the DEV environment (ADR-003).
-- Run in Snowsight as ACCOUNTADMIN before the first Liquibase run; see
-- docs/guides/snowflake-setup.md. Everything else is created by Liquibase.
-- Replace <DEPLOYER_DEV_PUBLIC_KEY> in Snowsight only; do not commit the key.

use role accountadmin;

-- Cost guard for the whole account: warn at 75%, suspend all warehouses at 100%.
create resource monitor if not exists rm_account
with credit_quota = 25
frequency = monthly
start_timestamp = immediately
triggers
on 75 percent do notify
on 100 percent do suspend;

alter account set resource_monitor = rm_account;

-- Warehouse and schema for Liquibase itself (change history of every environment).
create warehouse if not exists wh_deploy
with warehouse_size = xsmall
auto_suspend = 60
auto_resume = true
initially_suspended = true;

create database if not exists streampulse_admin;
create schema if not exists streampulse_admin.liquibase;

-- Deployer for DEV: creates and owns every object of the DEV environment.
create role if not exists deployer_dev;
grant create database on account to role deployer_dev;
grant create warehouse on account to role deployer_dev;
grant create role on account to role deployer_dev;
grant create user on account to role deployer_dev;
grant usage on warehouse wh_deploy to role deployer_dev;
grant usage on database streampulse_admin to role deployer_dev;
grant usage, create table on schema streampulse_admin.liquibase to role deployer_dev;
-- SYSADMIN keeps control over everything the deployer creates.
grant role deployer_dev to role sysadmin;

create user if not exists svc_deployer_dev
    type = service
    default_role = deployer_dev
    default_warehouse = wh_deploy
    rsa_public_key = '<DEPLOYER_DEV_PUBLIC_KEY>'
    comment = 'Liquibase, loader, and tests for DEV (key-pair authentication)';

grant role deployer_dev to user svc_deployer_dev;
