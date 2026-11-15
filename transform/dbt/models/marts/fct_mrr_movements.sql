with movements as (
    select * from {{ ref('int_mrr_movements_classified') }}
),

final as (
    select
        calendar_month::date as calendar_month,
        customer_id::number(38, 0) as customer_id,
        market_code::varchar as market_code,
        movement_type::varchar as movement_type,
        currency_code::varchar as currency_code,
        mrr_change_local::number(38, 6) as mrr_change_local,
        mrr_change_eur::number(38, 6) as mrr_change_eur
    from movements
)

select * from final
