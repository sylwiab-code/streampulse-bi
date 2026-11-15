-- Latest version of each campaigns row: the newest batch holds the current snapshot.
with source as (
    select * from {{ source('streampulse_raw', 'campaigns') }}
),

latest as (
    select
        campaign_id,
        campaign_name,
        market_code,
        channel as acquisition_channel,
        start_date,
        end_date,
        {{ load_date_from_file_name('_file_name') }} as load_date
    from source
    qualify row_number() over (
        partition by campaign_id order by load_date desc, _file_row_number asc
    ) = 1
)

select * from latest
