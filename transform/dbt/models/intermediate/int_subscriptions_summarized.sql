-- One row per subscription with its trial outcome, paid start, and churn (ADR-002, KPI rules):
-- churn date = end of the paid period (voluntary) or the last failed payment retry
-- (involuntary); an expired trial is not churn.
with subscriptions as (
    select * from {{ ref('stg_streampulse__subscriptions') }}
),

events as (
    select * from {{ ref('stg_streampulse__subscription_events') }}
),

milestones as (
    select
        subscription_id,
        min(iff(event_type = 'trial_started', event_at, null)) as trial_started_at,
        min(iff(event_type = 'trial_converted', event_at, null)) as trial_converted_at,
        min(iff(event_type = 'trial_expired', event_at, null)) as trial_expired_at,
        min(
            iff(
                event_type in ('trial_converted', 'subscription_started', 'reactivated'),
                event_at,
                null
            )
        ) as paid_started_at,
        min(iff(event_type = 'cancelled', event_at, null)) as cancelled_at,
        min(iff(event_type = 'cancelled', cancellation_type, null)) as churn_type,
        min(iff(event_type = 'cancelled', effective_date, null)) as churn_date
    from events
    group by subscription_id
),

summarized as (
    select
        subscriptions.subscription_id,
        subscriptions.customer_id,
        subscriptions.market_code,
        subscriptions.initial_plan_id,
        subscriptions.created_at,
        subscriptions.is_trial,
        subscriptions.is_reactivation,
        milestones.trial_started_at,
        coalesce(milestones.trial_converted_at, milestones.trial_expired_at) as trial_ended_at,
        case
            when not subscriptions.is_trial then null
            when milestones.trial_converted_at is not null then 'converted'
            when milestones.trial_expired_at is not null then 'expired'
            else 'in_trial'
        end as trial_outcome,
        milestones.paid_started_at,
        milestones.paid_started_at::date as paid_start_date,
        milestones.cancelled_at,
        milestones.churn_type,
        milestones.churn_date
    from subscriptions
    left join milestones
        on subscriptions.subscription_id = milestones.subscription_id
)

select * from summarized
