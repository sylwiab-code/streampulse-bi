with movements as (
    select * from {{ ref('fct_mrr_movements') }}
),

aggregated as (
    select
        calendar_month,
        market_code,
        movement_type,
        currency_code,
        count(distinct customer_id) as customers,
        sum(mrr_change_local) as mrr_change_local,
        sum(mrr_change_eur) as mrr_change_eur
    from movements
    group by calendar_month, market_code, movement_type, currency_code
)

select * from aggregated
