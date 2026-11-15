-- Latest version of each plans row: the newest batch holds the current snapshot.
with source as (
    select * from {{ source('streampulse_raw', 'plans') }}
),

latest as (
    select
        plan_id,
        plan_name,
        tier as tier_name,
        tier_rank,
        billing_period,
        billing_months,
        {{ load_date_from_file_name('_file_name') }} as load_date
    from source
    qualify row_number() over (
        partition by plan_id order by load_date desc, _file_row_number asc
    ) = 1
)

select * from latest
