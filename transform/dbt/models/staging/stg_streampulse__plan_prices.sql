-- Latest version of each plan_prices row: the newest batch holds the current snapshot.
with source as (
    select * from {{ source('streampulse_raw', 'plan_prices') }}
),

latest as (
    select
        price_id,
        market_code,
        plan_id,
        currency_code,
        price as price_local,
        valid_from,
        valid_to,
        {{ load_date_from_file_name('_file_name') }} as load_date
    from source
    qualify row_number() over (
        partition by price_id order by load_date desc, _file_row_number asc
    ) = 1
)

select * from latest
