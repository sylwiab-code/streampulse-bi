with campaigns as (
    select * from {{ ref('stg_streampulse__campaigns') }}
),

final as (
    select
        campaign_id::number(38, 0) as campaign_id,
        campaign_name::varchar as campaign_name,
        market_code::varchar as market_code,
        acquisition_channel::varchar as acquisition_channel,
        start_date::date as start_date,
        end_date::date as end_date
    from campaigns
)

select * from final
