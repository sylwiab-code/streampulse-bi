-- Customer attributes derived from behavior: first paid date and cohort month, and the
-- repeat-trial flag (KPI rule: an earlier customer with the same normalized email hash had a
-- trial that expired without conversion before this customer signed up).
with customers as (
    select * from {{ ref('stg_streampulse__customers') }}
),

subscriptions as (
    select * from {{ ref('int_subscriptions_summarized') }}
),

payments as (
    select * from {{ ref('int_payments_enriched') }}
),

first_payments as (
    select
        customer_id,
        min(attempted_date) as first_paid_date
    from payments
    where payment_status = 'succeeded'
    group by customer_id
),

expired_trials as (
    select
        customer_id,
        trial_ended_at
    from subscriptions
    where trial_outcome = 'expired'
),

repeat_trials as (
    select distinct later_customers.customer_id
    from customers as later_customers
    inner join customers as earlier_customers
        on
            later_customers.email_hash = earlier_customers.email_hash
            and later_customers.created_at > earlier_customers.created_at
    inner join expired_trials
        on
            earlier_customers.customer_id = expired_trials.customer_id
            and later_customers.created_at >= expired_trials.trial_ended_at
),

flagged as (
    select
        customers.customer_id,
        customers.market_code,
        customers.created_at,
        customers.signup_date,
        first_payments.first_paid_date,
        date_trunc(month, first_payments.first_paid_date) as cohort_month,
        repeat_trials.customer_id is not null as is_repeat_trial
    from customers
    left join first_payments
        on customers.customer_id = first_payments.customer_id
    left join repeat_trials
        on customers.customer_id = repeat_trials.customer_id
)

select * from flagged
