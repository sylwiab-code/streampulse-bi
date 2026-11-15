with source as (
    select * from {{ source('streampulse_raw', 'subscriptions') }}
),

deduplicated as (
    select
        subscription_id,
        customer_id,
        market_code,
        plan_id as initial_plan_id,
        created_at,
        is_trial,
        is_reactivation
    from source
    qualify row_number() over (
        partition by subscription_id order by _loaded_at asc, _file_row_number asc
    ) = 1
)

select * from deduplicated
