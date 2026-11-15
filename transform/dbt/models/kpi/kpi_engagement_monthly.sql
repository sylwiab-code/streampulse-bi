with sessions as (
    select * from {{ ref('fct_viewing_sessions') }}
),

titles as (
    select * from {{ ref('dim_content') }}
),

customers as (
    select * from {{ ref('dim_customer') }}
),

aggregated as (
    select
        date_trunc(month, sessions.started_date) as calendar_month,
        customers.market_code,
        titles.genre_name,
        count(*) as sessions,
        count(distinct sessions.customer_id) as viewers,
        sum(sessions.watch_hours) as watch_hours
    from sessions
    inner join titles
        on sessions.title_id = titles.title_id
    inner join customers
        on sessions.customer_id = customers.customer_id
    group by date_trunc(month, sessions.started_date), customers.market_code, titles.genre_name
)

select * from aggregated
