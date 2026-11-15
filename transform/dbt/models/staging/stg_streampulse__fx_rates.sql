with source as (
    select * from {{ source('streampulse_raw', 'fx_rates') }}
),

deduplicated as (
    select
        rate_date,
        currency_code,
        units_per_eur
    from source
    qualify row_number() over (
        partition by rate_date, currency_code order by _loaded_at desc, _file_row_number asc
    ) = 1
)

select * from deduplicated
