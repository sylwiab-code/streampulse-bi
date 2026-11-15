-- One row per subscription and day in trial or paid status (KPI rules): paid days run from
-- the paid start to the churn date (exclusive), including payment-retry days.
with subscriptions as (
    select * from {{ ref('int_subscriptions_summarized') }}
),

days as (
    select date_day from {{ ref('int_days_generated') }}
),

mrr_periods as (
    select * from {{ ref('int_mrr_periods_derived') }}
),

markets as (
    select * from {{ ref('stg_streampulse__markets') }}
),

fx_rates as (
    select * from {{ ref('stg_streampulse__fx_rates') }}
),

plans as (
    select * from {{ ref('stg_streampulse__plans') }}
),

plan_prices as (
    select * from {{ ref('stg_streampulse__plan_prices') }}
),

-- Before the first successful payment (first payment still in retry), MRR is the list price
-- of the subscribed plan.
list_mrr as (
    select
        subscriptions.subscription_id,
        plan_prices.price_local / plans.billing_months as mrr_local
    from subscriptions
    inner join plans
        on subscriptions.initial_plan_id = plans.plan_id
    inner join plan_prices
        on
            subscriptions.market_code = plan_prices.market_code
            and subscriptions.initial_plan_id = plan_prices.plan_id
            and subscriptions.paid_start_date >= plan_prices.valid_from
            and subscriptions.paid_start_date <= coalesce(plan_prices.valid_to, '9999-12-31'::date)
),

trial_days as (
    select
        days.date_day,
        subscriptions.subscription_id,
        subscriptions.customer_id,
        subscriptions.market_code,
        subscriptions.initial_plan_id as plan_id,
        'trial' as subscription_status,
        0 as mrr_local
    from subscriptions
    inner join days
        on
            days.date_day >= subscriptions.trial_started_at::date
            and days.date_day < coalesce(subscriptions.trial_ended_at::date, '9999-12-31'::date)
    where subscriptions.is_trial
),

paid_days as (
    select
        days.date_day,
        subscriptions.subscription_id,
        subscriptions.customer_id,
        subscriptions.market_code,
        coalesce(mrr_periods.plan_id, subscriptions.initial_plan_id) as plan_id,
        'paid' as subscription_status,
        coalesce(mrr_periods.mrr_local, list_mrr.mrr_local) as mrr_local
    from subscriptions
    inner join days
        on
            subscriptions.paid_start_date <= days.date_day
            and coalesce(subscriptions.churn_date, '9999-12-31'::date) > days.date_day
    left join list_mrr
        on subscriptions.subscription_id = list_mrr.subscription_id
    left join mrr_periods
        on
            subscriptions.subscription_id = mrr_periods.subscription_id
            and days.date_day >= mrr_periods.valid_from
            and (mrr_periods.valid_until is null or days.date_day < mrr_periods.valid_until)
),

all_days as (
    select * from trial_days
    union all
    select * from paid_days
),

converted as (
    select
        all_days.date_day,
        all_days.subscription_id,
        all_days.customer_id,
        all_days.market_code,
        all_days.plan_id,
        all_days.subscription_status,
        markets.currency_code,
        all_days.mrr_local,
        all_days.mrr_local / fx_rates.units_per_eur as mrr_eur
    from all_days
    inner join markets
        on all_days.market_code = markets.market_code
    left join fx_rates
        on
            all_days.date_day = fx_rates.rate_date
            and markets.currency_code = fx_rates.currency_code
)

select * from converted
