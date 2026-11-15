-- Monthly cohorts by first payment month (KPI rule): a customer is retained in month k if
-- active (MRR > 0) at the end of month k; returning customers count again once active.
with customers as (
    select * from {{ ref('int_customers_flagged') }}
    where cohort_month is not null
),

customer_months as (
    select * from {{ ref('int_customer_months_aggregated') }}
    where mrr_local > 0
),

months as (
    select * from {{ ref('int_months_generated') }}
),

cohort_sizes as (
    select
        cohort_month,
        market_code,
        count(*) as cohort_customers
    from customers
    group by cohort_month, market_code
),

offsets as (
    select
        cohort_sizes.cohort_month,
        cohort_sizes.market_code,
        cohort_sizes.cohort_customers,
        months.calendar_month,
        datediff(month, cohort_sizes.cohort_month, months.calendar_month)
            as months_since_first_payment
    from cohort_sizes
    inner join months
        on
            cohort_sizes.cohort_month <= months.calendar_month
            and datediff(month, cohort_sizes.cohort_month, months.calendar_month)
            <= {{ var('cohort_max_months') }}
),

retained as (
    select
        customers.cohort_month,
        customers.market_code,
        customer_months.calendar_month,
        count(*) as retained_customers
    from customers
    inner join customer_months
        on customers.customer_id = customer_months.customer_id
    group by customers.cohort_month, customers.market_code, customer_months.calendar_month
),

final as (
    select
        offsets.cohort_month::date as cohort_month,
        offsets.market_code::varchar as market_code,
        offsets.months_since_first_payment::number(38, 0) as months_since_first_payment,
        offsets.calendar_month::date as calendar_month,
        offsets.cohort_customers::number(38, 0) as cohort_customers,
        coalesce(retained.retained_customers, 0)::number(38, 0) as retained_customers
    from offsets
    left join retained
        on
            offsets.cohort_month = retained.cohort_month
            and offsets.market_code = retained.market_code
            and offsets.calendar_month = retained.calendar_month
)

select * from final
