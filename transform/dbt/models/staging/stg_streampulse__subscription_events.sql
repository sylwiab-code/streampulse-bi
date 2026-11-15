-- Incremental: each run reads only rows loaded since the last run, so late-arriving rows are
-- picked up when they land; the merge on event_id removes the duplicates the source sends.
{{
    config(
        materialized='incremental',
        unique_key='event_id',
        incremental_strategy='merge',
        on_schema_change='append_new_columns'
    )
}}

with source as (
    select raw_rows.* from {{ source('streampulse_raw', 'subscription_events') }} as raw_rows
    {% if is_incremental() %}
        where raw_rows._loaded_at > (select max(existing.loaded_at) from {{ this }} as existing)
    {% endif %}
),

deduplicated as (
    select
        event_id,
        subscription_id,
        customer_id,
        event_type,
        event_at,
        plan_id,
        previous_plan_id,
        cancellation_type,
        effective_date,
        _loaded_at as loaded_at
    from source
    qualify row_number() over (
        partition by event_id order by _loaded_at asc, _file_row_number asc
    ) = 1
)

select * from deduplicated
