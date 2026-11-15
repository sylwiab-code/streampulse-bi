with subscriptions as (
    select * from {{ ref('fct_subscriptions') }}
    where is_trial
),

customers as (
    select * from {{ ref('dim_customer') }}
),

aggregated as (
    select
        date_trunc(month, subscriptions.trial_start_date) as trial_start_month,
        subscriptions.market_code,
        customers.acquisition_channel,
        customers.campaign_id,
        count(*) as trials_started,
        count_if(subscriptions.trial_outcome = 'converted') as trials_converted,
        count_if(subscriptions.trial_outcome = 'expired') as trials_expired,
        count_if(subscriptions.trial_outcome = 'in_trial') as trials_open
    from subscriptions
    inner join customers
        on subscriptions.customer_id = customers.customer_id
    group by
        date_trunc(month, subscriptions.trial_start_date),
        subscriptions.market_code,
        customers.acquisition_channel,
        customers.campaign_id
),

final as (
    select
        *,
        trials_converted / trials_started as conversion_rate
    from aggregated
)

select * from final
