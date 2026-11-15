-- Incremental merge on session_id: late sessions are added when they land, and duplicates
-- are merged. Sessions without customer_id (0.1%) cannot be attributed and are left out.
{{
    config(
        materialized='incremental',
        unique_key='session_id',
        incremental_strategy='merge',
        on_schema_change='fail'
    )
}}

with sessions as (
    select staged.* from {{ ref('stg_streampulse__viewing_sessions') }} as staged
    where
        staged.customer_id is not null
        {% if is_incremental() %}
            and staged.loaded_at > (select max(existing.loaded_at) from {{ this }} as existing)
        {% endif %}
),

titles as (
    select * from {{ ref('stg_streampulse__content_catalog') }}
),

final as (
    select
        sessions.session_id::number(38, 0) as session_id,
        sessions.customer_id::number(38, 0) as customer_id,
        sessions.title_id::number(38, 0) as title_id,
        sessions.started_at::timestamp_ntz as started_at,
        sessions.started_at::date as started_date,
        sessions.watch_minutes::number(38, 0) as watch_minutes,
        (sessions.watch_minutes / 60)::number(38, 4) as watch_hours,
        least(sessions.watch_minutes / titles.runtime_minutes, 1)::number(38, 6)
            as completion_rate,
        sessions.device_type::varchar as device_type,
        sessions.app_version::varchar as app_version,
        sessions.loaded_at::timestamp_ltz as loaded_at
    from sessions
    left join titles
        on sessions.title_id = titles.title_id
)

select * from final
