with retention as (
    select * from {{ ref('fct_cohort_retention') }}
),

final as (
    select
        cohort_month,
        market_code,
        months_since_first_payment,
        calendar_month,
        cohort_customers,
        retained_customers,
        retained_customers / nullif(cohort_customers, 0) as retention_rate
    from retention
)

select * from final
