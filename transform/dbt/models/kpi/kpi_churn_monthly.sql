with subscriptions as (
    select * from {{ ref('fct_subscriptions') }}
),

subscription_days as (
    select * from {{ ref('fct_subscription_daily') }}
    where subscription_status = 'paid'
),

last_loaded as (
    select max(date_day) as last_day from subscription_days
),

active_at_start as (
    select
        date_day as calendar_month,
        market_code,
        count(*) as active_at_month_start
    from subscription_days
    where date_day = date_trunc(month, date_day)
    group by date_day, market_code
),

churned as (
    select
        date_trunc(month, subscriptions.churn_date) as calendar_month,
        subscriptions.market_code,
        count_if(subscriptions.churn_type = 'voluntary') as churned_voluntary,
        count_if(subscriptions.churn_type = 'involuntary') as churned_involuntary
    from subscriptions
    cross join last_loaded
    where subscriptions.churn_date <= last_loaded.last_day
    group by date_trunc(month, subscriptions.churn_date), subscriptions.market_code
),

combined as (
    select
        coalesce(active_at_start.calendar_month, churned.calendar_month) as calendar_month,
        coalesce(active_at_start.market_code, churned.market_code) as market_code,
        coalesce(active_at_start.active_at_month_start, 0) as active_at_month_start,
        coalesce(churned.churned_voluntary, 0) as churned_voluntary,
        coalesce(churned.churned_involuntary, 0) as churned_involuntary
    from active_at_start
    full outer join churned
        on
            active_at_start.calendar_month = churned.calendar_month
            and active_at_start.market_code = churned.market_code
),

final as (
    select
        calendar_month,
        market_code,
        active_at_month_start,
        churned_voluntary,
        churned_involuntary,
        churned_voluntary + churned_involuntary as churned_subscribers,
        (churned_voluntary + churned_involuntary) / nullif(active_at_month_start, 0) as churn_rate
    from combined
)

select * from final
