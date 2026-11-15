-- Reporting calendar (full years, from dbt_project.yml vars) for Power BI time intelligence.
with numbered as (
    select row_number() over (order by seq4()) - 1 as day_offset
    from table(generator(rowcount => 5000))
),

days as (
    select dateadd(day, day_offset, '{{ var("calendar_start_date") }}'::date) as date_day
    from numbered
    where
        day_offset <= datediff(
            day,
            '{{ var("calendar_start_date") }}'::date,
            '{{ var("calendar_end_date") }}'::date
        )
),

final as (
    select
        date_day::date as date_day,
        date_trunc(month, date_day)::date as calendar_month,
        last_day(date_day)::date as month_end_date,
        date_trunc(quarter, date_day)::date as calendar_quarter,
        year(date_day)::number(38, 0) as calendar_year,
        month(date_day)::number(38, 0) as month_number,
        monthname(date_day)::varchar as month_name,
        weekiso(date_day)::number(38, 0) as iso_week_number,
        dayofweekiso(date_day)::number(38, 0) as iso_day_of_week,
        dayname(date_day)::varchar as day_name,
        (dayofweekiso(date_day) in (6, 7))::boolean as is_weekend
    from days
)

select * from final
