-- MRR from each successful payment until the next one (KPI rule: MRR = the plan price paid,
-- annual plans divided by 12). During payment retries the previous MRR stays in force.
with payments as (
    select * from {{ ref('int_payments_enriched') }}
    where payment_status = 'succeeded'
),

periods as (
    select
        subscription_id,
        customer_id,
        market_code,
        plan_id,
        currency_code,
        attempted_date as valid_from,
        lead(attempted_date) over (
            partition by subscription_id order by attempted_at
        ) as valid_until,
        amount_local / billing_months as mrr_local
    from payments
)

select * from periods
