with payments as (
    select * from {{ ref('int_payments_enriched') }}
),

final as (
    select
        payment_id::number(38, 0) as payment_id,
        subscription_id::number(38, 0) as subscription_id,
        customer_id::number(38, 0) as customer_id,
        market_code::varchar as market_code,
        plan_id::varchar as plan_id,
        billing_period_start::date as billing_period_start,
        attempt_number::number(38, 0) as attempt_number,
        attempted_at::timestamp_ntz as attempted_at,
        attempted_date::date as attempted_date,
        payment_status::varchar as payment_status,
        failure_reason::varchar as failure_reason,
        currency_code::varchar as currency_code,
        amount_local::number(38, 2) as amount_local,
        amount_eur::number(38, 6) as amount_eur
    from payments
)

select * from final
