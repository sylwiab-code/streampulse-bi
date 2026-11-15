-- Opening MRR + all movements = closing MRR, per market and month, in local currency and in
-- EUR (the EUR bridge needs the fx_effect rows). Returns the months that do not reconcile.
with closing as (
    select
        calendar_month,
        market_code,
        sum(mrr_local) as closing_local,
        sum(mrr_eur) as closing_eur
    from {{ ref('int_customer_months_aggregated') }}
    group by calendar_month, market_code
),

movements as (
    select
        calendar_month,
        market_code,
        sum(mrr_change_local) as change_local,
        sum(mrr_change_eur) as change_eur
    from {{ ref('fct_mrr_movements') }}
    group by calendar_month, market_code
),

bridge as (
    select
        closing.calendar_month,
        closing.market_code,
        closing.closing_local,
        closing.closing_eur,
        coalesce(
            lag(closing.closing_local) over (
                partition by closing.market_code order by closing.calendar_month
            ),
            0
        ) + coalesce(movements.change_local, 0) as expected_local,
        coalesce(
            lag(closing.closing_eur) over (
                partition by closing.market_code order by closing.calendar_month
            ),
            0
        ) + coalesce(movements.change_eur, 0) as expected_eur
    from closing
    left join movements
        on
            closing.calendar_month = movements.calendar_month
            and closing.market_code = movements.market_code
)

select *
from bridge
where abs(closing_local - expected_local) > 0.01 or abs(closing_eur - expected_eur) > 0.01
