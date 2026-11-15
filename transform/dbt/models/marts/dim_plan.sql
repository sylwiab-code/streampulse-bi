with plans as (
    select * from {{ ref('stg_streampulse__plans') }}
),

final as (
    select
        plan_id::varchar as plan_id,
        plan_name::varchar as plan_name,
        tier_name::varchar as tier_name,
        tier_rank::number(38, 0) as tier_rank,
        billing_period::varchar as billing_period,
        billing_months::number(38, 0) as billing_months
    from plans
)

select * from final
