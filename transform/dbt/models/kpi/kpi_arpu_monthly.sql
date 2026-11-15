with subscription_days as (
    select * from {{ ref('fct_subscription_daily') }}
    where subscription_status = 'paid'
),

last_loaded as (
    select max(date_day) as last_day from subscription_days
),

month_end as (
    select subscription_days.*
    from subscription_days
    cross join last_loaded
    where
        subscription_days.date_day
        = least(last_day(subscription_days.date_day), last_loaded.last_day)
),

aggregated as (
    select
        date_trunc(month, date_day) as calendar_month,
        market_code,
        plan_id,
        currency_code,
        count(*) as active_subscribers,
        sum(mrr_local) as mrr_local,
        sum(mrr_eur) as mrr_eur,
        sum(mrr_local) / count(*) as arpu_local,
        sum(mrr_eur) / count(*) as arpu_eur
    from month_end
    group by date_trunc(month, date_day), market_code, plan_id, currency_code
)

select * from aggregated
