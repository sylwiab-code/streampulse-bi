-- Latest version of each currencies row: the newest batch holds the current snapshot.
with source as (
    select * from {{ source('streampulse_raw', 'currencies') }}
),

latest as (
    select
        currency_code,
        currency_name,
        {{ load_date_from_file_name('_file_name') }} as load_date
    from source
    qualify row_number() over (
        partition by currency_code order by load_date desc, _file_row_number asc
    ) = 1
)

select * from latest
