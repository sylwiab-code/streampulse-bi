with subscription_days as (
    select * from {{ ref('fct_subscription_daily') }}
),

aggregated as (
    select
        date_day,
        market_code,
        plan_id,
        currency_code,
        count_if(subscription_status = 'paid') as active_subscribers,
        count_if(subscription_status = 'trial') as trialists,
        sum(mrr_local) as mrr_local,
        sum(mrr_eur) as mrr_eur,
        sum(mrr_eur) * 12 as arr_eur
    from subscription_days
    group by date_day, market_code, plan_id, currency_code
)

select * from aggregated
