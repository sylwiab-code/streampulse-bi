-- Customers without PII: only behavioral attributes and the repeat-trial flag.
with customers as (
    select * from {{ ref('int_customers_flagged') }}
),

attribution as (
    select * from {{ ref('stg_streampulse__acquisition_attribution') }}
),

final as (
    select
        customers.customer_id::number(38, 0) as customer_id,
        customers.market_code::varchar as market_code,
        customers.created_at::timestamp_ntz as signup_at,
        customers.signup_date::date as signup_date,
        attribution.acquisition_channel::varchar as acquisition_channel,
        attribution.campaign_id::number(38, 0) as campaign_id,
        customers.first_paid_date::date as first_paid_date,
        customers.cohort_month::date as cohort_month,
        customers.is_repeat_trial::boolean as is_repeat_trial
    from customers
    left join attribution
        on customers.customer_id = attribution.customer_id
)

select * from final
