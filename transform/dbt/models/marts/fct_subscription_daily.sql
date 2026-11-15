-- Periodic snapshot: one row per subscription and day in trial or paid status.
with subscription_days as (
    select * from {{ ref('int_subscription_days_expanded') }}
),

final as (
    select
        date_day::date as date_day,
        subscription_id::number(38, 0) as subscription_id,
        customer_id::number(38, 0) as customer_id,
        market_code::varchar as market_code,
        plan_id::varchar as plan_id,
        subscription_status::varchar as subscription_status,
        currency_code::varchar as currency_code,
        mrr_local::number(38, 6) as mrr_local,
        mrr_eur::number(38, 6) as mrr_eur
    from subscription_days
)

select * from final
