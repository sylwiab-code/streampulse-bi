-- CAC per paid channel, with the market's ARPU and churn rate reused from the KPI models
-- (one definition each) to derive LTV and LTV/CAC.
with spend as (
    select * from {{ ref('fct_campaign_spend') }}
),

customers as (
    select * from {{ ref('dim_customer') }}
),

channels as (
    select * from {{ ref('dim_channel') }}
),

arpu as (
    select * from {{ ref('kpi_arpu_monthly') }}
),

churn as (
    select * from {{ ref('kpi_churn_monthly') }}
),

monthly_spend as (
    select
        date_trunc(month, spend_date) as calendar_month,
        market_code,
        acquisition_channel,
        sum(spend_eur) as spend_eur
    from spend
    group by date_trunc(month, spend_date), market_code, acquisition_channel
),

new_paying as (
    select
        date_trunc(month, customers.first_paid_date) as calendar_month,
        customers.market_code,
        customers.acquisition_channel,
        count(*) as new_paying_customers
    from customers
    inner join channels
        on customers.acquisition_channel = channels.acquisition_channel
    where channels.is_paid_channel and customers.first_paid_date is not null
    group by
        date_trunc(month, customers.first_paid_date),
        customers.market_code,
        customers.acquisition_channel
),

market_arpu as (
    select
        calendar_month,
        market_code,
        sum(mrr_eur) / nullif(sum(active_subscribers), 0) as arpu_eur
    from arpu
    group by calendar_month, market_code
),

acquisition as (
    select
        coalesce(monthly_spend.calendar_month, new_paying.calendar_month) as calendar_month,
        coalesce(monthly_spend.market_code, new_paying.market_code) as market_code,
        coalesce(monthly_spend.acquisition_channel, new_paying.acquisition_channel)
            as acquisition_channel,
        coalesce(monthly_spend.spend_eur, 0) as spend_eur,
        coalesce(new_paying.new_paying_customers, 0) as new_paying_customers
    from monthly_spend
    full outer join new_paying
        on
            monthly_spend.calendar_month = new_paying.calendar_month
            and monthly_spend.market_code = new_paying.market_code
            and monthly_spend.acquisition_channel = new_paying.acquisition_channel
),

final as (
    select
        acquisition.calendar_month,
        acquisition.market_code,
        acquisition.acquisition_channel,
        acquisition.spend_eur,
        acquisition.new_paying_customers,
        acquisition.spend_eur / nullif(acquisition.new_paying_customers, 0) as cac_eur,
        market_arpu.arpu_eur,
        churn.churn_rate,
        market_arpu.arpu_eur / nullif(churn.churn_rate, 0) as ltv_eur,
        (market_arpu.arpu_eur / nullif(churn.churn_rate, 0))
        / nullif(acquisition.spend_eur / nullif(acquisition.new_paying_customers, 0), 0)
            as ltv_to_cac
    from acquisition
    left join market_arpu
        on
            acquisition.calendar_month = market_arpu.calendar_month
            and acquisition.market_code = market_arpu.market_code
    left join churn
        on
            acquisition.calendar_month = churn.calendar_month
            and acquisition.market_code = churn.market_code
)

select * from final
