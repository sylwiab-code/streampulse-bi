-- Incremental: each run reads only rows loaded since the last run, so late-arriving rows are
-- picked up when they land; the merge on payment_id removes the duplicates the source sends.
{{
    config(
        materialized='incremental',
        unique_key='payment_id',
        incremental_strategy='merge',
        on_schema_change='append_new_columns'
    )
}}

with source as (
    select raw_rows.* from {{ source('streampulse_raw', 'payments') }} as raw_rows
    {% if is_incremental() %}
        where raw_rows._loaded_at > (select max(existing.loaded_at) from {{ this }} as existing)
    {% endif %}
),

deduplicated as (
    select
        payment_id,
        subscription_id,
        customer_id,
        plan_id,
        billing_period_start,
        attempt_number,
        attempted_at,
        amount as amount_local,
        currency_code,
        status as payment_status,
        failure_reason,
        _loaded_at as loaded_at
    from source
    qualify row_number() over (
        partition by payment_id order by _loaded_at asc, _file_row_number asc
    ) = 1
)

select * from deduplicated
