-- Monthly MRR movements per customer (KPI rules, ADR-002), comparing month-end MRR:
-- new (first paid month-end), reactivation (paid again after zero), expansion (upgrade or
-- price increase), contraction (downgrade), churn (to zero). Amounts are in local currency
-- and in EUR at this month's rate; the fx_effect row revalues last month's EUR MRR at this
-- month's rate, so opening EUR MRR + all movements = closing EUR MRR.
with customer_months as (
    select * from {{ ref('int_customer_months_aggregated') }}
),

compared as (
    select
        calendar_month,
        customer_id,
        market_code,
        currency_code,
        mrr_local,
        mrr_eur,
        month_end_units_per_eur,
        has_paid_before,
        coalesce(
            lag(mrr_local) over (partition by customer_id order by calendar_month), 0
        ) as previous_mrr_local,
        coalesce(
            lag(mrr_eur) over (partition by customer_id order by calendar_month), 0
        ) as previous_mrr_eur
    from customer_months
),

classified as (
    select
        *,
        case
            when previous_mrr_local = 0 and mrr_local > 0 and not has_paid_before then 'new'
            when previous_mrr_local = 0 and mrr_local > 0 then 'reactivation'
            when previous_mrr_local > 0 and mrr_local = 0 then 'churn'
            when mrr_local > previous_mrr_local then 'expansion'
            when mrr_local < previous_mrr_local then 'contraction'
        end as movement_type
    from compared
),

mrr_movements as (
    select
        calendar_month,
        customer_id,
        market_code,
        currency_code,
        movement_type,
        mrr_local - previous_mrr_local as mrr_change_local,
        (mrr_local - previous_mrr_local) / month_end_units_per_eur as mrr_change_eur
    from classified
    where movement_type is not null
),

fx_effects as (
    select
        calendar_month,
        customer_id,
        market_code,
        currency_code,
        'fx_effect' as movement_type,
        0 as mrr_change_local,
        previous_mrr_local / month_end_units_per_eur - previous_mrr_eur as mrr_change_eur
    from compared
    where
        previous_mrr_local > 0
        and round(previous_mrr_local / month_end_units_per_eur - previous_mrr_eur, 6) != 0
),

movements as (
    select * from mrr_movements
    union all
    select * from fx_effects
)

select * from movements
