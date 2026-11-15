-- One row per month; the month-end date of the current month is the last loaded day.
with days as (
    select date_day from {{ ref('int_days_generated') }}
),

months as (
    select
        date_trunc(month, date_day) as calendar_month,
        max(date_day) as month_end_date,
        max(date_day) = last_day(date_trunc(month, date_day)) as is_complete_month
    from days
    group by date_trunc(month, date_day)
)

select * from months
