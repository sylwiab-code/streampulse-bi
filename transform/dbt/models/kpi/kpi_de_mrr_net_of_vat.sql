-- Local extension for Germany (global vs local pattern): reuses the global KPI model and
-- only adds the local view (MRR net of VAT); it never recomputes the global logic.
{{ config(materialized='view') }}

with subscribers as (
    select * from {{ ref('kpi_subscribers_daily') }}
    where market_code = 'DE'
),

final as (
    select
        date_day,
        plan_id,
        active_subscribers,
        mrr_local as mrr_gross,
        mrr_local / (1 + {{ var('de_vat_rate') }}) as mrr_net_of_vat,
        {{ var('de_vat_rate') }} as vat_rate
    from subscribers
)

select * from final
