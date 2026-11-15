-- Payment attempts with the customer recovered from the subscription (0.1% arrive without
-- customer_id), the plan's billing months, and the amount in EUR at the day's rate.
with payments as (
    select * from {{ ref('stg_streampulse__payments') }}
),

subscriptions as (
    select * from {{ ref('stg_streampulse__subscriptions') }}
),

plans as (
    select * from {{ ref('stg_streampulse__plans') }}
),

fx_rates as (
    select * from {{ ref('stg_streampulse__fx_rates') }}
),

enriched as (
    select
        payments.payment_id,
        payments.subscription_id,
        coalesce(payments.customer_id, subscriptions.customer_id) as customer_id,
        subscriptions.market_code,
        payments.plan_id,
        plans.billing_months,
        payments.billing_period_start,
        payments.attempt_number,
        payments.attempted_at,
        payments.attempted_at::date as attempted_date,
        payments.payment_status,
        payments.failure_reason,
        payments.currency_code,
        payments.amount_local,
        payments.amount_local / fx_rates.units_per_eur as amount_eur
    from payments
    left join subscriptions
        on payments.subscription_id = subscriptions.subscription_id
    left join plans
        on payments.plan_id = plans.plan_id
    left join fx_rates
        on
            payments.attempted_at::date = fx_rates.rate_date
            and payments.currency_code = fx_rates.currency_code
)

select * from enriched
