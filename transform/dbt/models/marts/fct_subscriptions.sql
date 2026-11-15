-- Accumulating snapshot: one row per subscription with trial, paid start, and churn.
with subscriptions as (
    select * from {{ ref('int_subscriptions_summarized') }}
),

final as (
    select
        subscription_id::number(38, 0) as subscription_id,
        customer_id::number(38, 0) as customer_id,
        market_code::varchar as market_code,
        initial_plan_id::varchar as initial_plan_id,
        created_at::timestamp_ntz as created_at,
        is_trial::boolean as is_trial,
        is_reactivation::boolean as is_reactivation,
        trial_started_at::date as trial_start_date,
        trial_ended_at::date as trial_end_date,
        trial_outcome::varchar as trial_outcome,
        paid_start_date::date as paid_start_date,
        churn_date::date as churn_date,
        churn_type::varchar as churn_type
    from subscriptions
)

select * from final
