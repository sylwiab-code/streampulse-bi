with markets as (
    select * from {{ ref('stg_streampulse__markets') }}
),

currencies as (
    select * from {{ ref('stg_streampulse__currencies') }}
),

final as (
    select
        markets.market_code::varchar as market_code,
        markets.market_name::varchar as market_name,
        markets.currency_code::varchar as currency_code,
        currencies.currency_name::varchar as currency_name
    from markets
    left join currencies
        on markets.currency_code = currencies.currency_code
)

select * from final
