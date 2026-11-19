with movements as (
    select * from {{ ref('int_mrr_movements_classified') }}
),

final as (
    select
        calendar_month::date as calendar_month,
        customer_id::number(38, 0) as customer_id,
        market_code::varchar as market_code,
        movement_type::varchar as movement_type,
        case movement_type
            when 'new' then 1
            when 'reactivation' then 2
            when 'expansion' then 3
            when 'contraction' then 4
            when 'churn' then 5
            when 'fx_effect' then 6
        end::number(38, 0) as movement_type_rank,
        currency_code::varchar as currency_code,
        mrr_change_local::number(38, 6) as mrr_change_local,
        mrr_change_eur::number(38, 6) as mrr_change_eur
    from movements
)

select * from final
