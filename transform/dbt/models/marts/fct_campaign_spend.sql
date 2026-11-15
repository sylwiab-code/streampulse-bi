with spend as (
    select * from {{ ref('stg_streampulse__campaign_spend') }}
),

campaigns as (
    select * from {{ ref('stg_streampulse__campaigns') }}
),

fx_rates as (
    select * from {{ ref('stg_streampulse__fx_rates') }}
),

final as (
    select
        spend.spend_date::date as spend_date,
        spend.campaign_id::number(38, 0) as campaign_id,
        campaigns.market_code::varchar as market_code,
        campaigns.acquisition_channel::varchar as acquisition_channel,
        spend.currency_code::varchar as currency_code,
        spend.spend_local::number(38, 2) as spend_local,
        (spend.spend_local / fx_rates.units_per_eur)::number(38, 6) as spend_eur
    from spend
    left join campaigns
        on spend.campaign_id = campaigns.campaign_id
    left join fx_rates
        on
            spend.spend_date = fx_rates.rate_date
            and spend.currency_code = fx_rates.currency_code
)

select * from final
