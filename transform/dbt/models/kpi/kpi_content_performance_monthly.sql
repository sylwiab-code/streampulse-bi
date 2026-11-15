with sessions as (
    select * from {{ ref('fct_viewing_sessions') }}
),

aggregated as (
    select
        date_trunc(month, started_date) as calendar_month,
        title_id,
        count(*) as sessions,
        count(distinct customer_id) as reach,
        sum(watch_hours) as watch_hours,
        avg(completion_rate) as avg_completion_rate
    from sessions
    group by date_trunc(month, started_date), title_id
)

select * from aggregated
