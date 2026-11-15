with source as (
    select * from {{ source('streampulse_raw', 'acquisition_attribution') }}
),

deduplicated as (
    select
        customer_id,
        channel as acquisition_channel,
        campaign_id,
        attributed_at
    from source
    qualify row_number() over (
        partition by customer_id order by _loaded_at asc, _file_row_number asc
    ) = 1
)

select * from deduplicated
