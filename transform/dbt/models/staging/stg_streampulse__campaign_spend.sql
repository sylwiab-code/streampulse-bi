with source as (
    select * from {{ source('streampulse_raw', 'campaign_spend') }}
),

deduplicated as (
    select
        spend_date,
        campaign_id,
        currency_code,
        amount as spend_local
    from source
    qualify row_number() over (
        partition by spend_date, campaign_id order by _loaded_at desc, _file_row_number asc
    ) = 1
)

select * from deduplicated
