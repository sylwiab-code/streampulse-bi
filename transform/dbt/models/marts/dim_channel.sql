-- Acquisition channels; a channel is paid when it has campaigns (and therefore spend).
with attribution as (
    select * from {{ ref('stg_streampulse__acquisition_attribution') }}
),

campaigns as (
    select * from {{ ref('stg_streampulse__campaigns') }}
),

channels as (
    select distinct acquisition_channel from attribution
),

paid_channels as (
    select distinct acquisition_channel from campaigns
),

final as (
    select
        channels.acquisition_channel::varchar as acquisition_channel,
        (paid_channels.acquisition_channel is not null)::boolean as is_paid_channel
    from channels
    left join paid_channels
        on channels.acquisition_channel = paid_channels.acquisition_channel
)

select * from final
