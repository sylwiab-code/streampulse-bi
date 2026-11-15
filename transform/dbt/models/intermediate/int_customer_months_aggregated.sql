-- MRR per customer at each month end, with a zero row for every month after the first paid
-- month-end, so that churn and reactivation are visible to the movement classification.
with paid_days as (
    select * from {{ ref('int_subscription_days_expanded') }}
    where subscription_status = 'paid'
),

months as (
    select * from {{ ref('int_months_generated') }}
),

fx_rates as (
    select * from {{ ref('stg_streampulse__fx_rates') }}
),

month_end_mrr as (
    select
        months.calendar_month,
        paid_days.customer_id,
        sum(paid_days.mrr_local) as mrr_local,
        sum(paid_days.mrr_eur) as mrr_eur
    from paid_days
    inner join months
        on paid_days.date_day = months.month_end_date
    group by months.calendar_month, paid_days.customer_id
),

customers as (
    select
        paid_days.customer_id,
        any_value(paid_days.market_code) as market_code,
        any_value(paid_days.currency_code) as currency_code
    from paid_days
    group by paid_days.customer_id
),

first_months as (
    select
        customer_id,
        min(calendar_month) as first_month
    from month_end_mrr
    group by customer_id
),

grid as (
    select
        months.calendar_month,
        months.month_end_date,
        customers.customer_id,
        customers.market_code,
        customers.currency_code
    from first_months
    inner join customers
        on first_months.customer_id = customers.customer_id
    inner join months
        on first_months.first_month <= months.calendar_month
),

filled as (
    select
        grid.calendar_month,
        grid.customer_id,
        grid.market_code,
        grid.currency_code,
        coalesce(month_end_mrr.mrr_local, 0) as mrr_local,
        coalesce(month_end_mrr.mrr_eur, 0) as mrr_eur,
        fx_rates.units_per_eur as month_end_units_per_eur
    from grid
    left join month_end_mrr
        on
            grid.customer_id = month_end_mrr.customer_id
            and grid.calendar_month = month_end_mrr.calendar_month
    left join fx_rates
        on
            grid.month_end_date = fx_rates.rate_date
            and grid.currency_code = fx_rates.currency_code
),

flagged as (
    select
        *,
        coalesce(
            max(iff(mrr_local > 0, 1, 0)) over (
                partition by customer_id
                order by calendar_month
                rows between unbounded preceding and 1 preceding
            ),
            0
        ) = 1 as has_paid_before
    from filled
)

select * from flagged
