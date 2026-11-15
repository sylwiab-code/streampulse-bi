-- One row per day from the first to the last loaded day (the latest exchange rate).
with bounds as (
    select
        min(rate_date) as first_day,
        max(rate_date) as last_day
    from {{ ref('stg_streampulse__fx_rates') }}
),

numbered as (
    select row_number() over (order by seq4()) - 1 as day_offset
    from table(generator(rowcount => 5000))
),

days as (
    select dateadd(day, numbered.day_offset, bounds.first_day) as date_day
    from numbered
    cross join bounds
    where numbered.day_offset <= datediff(day, bounds.first_day, bounds.last_day)
)

select date_day from days
