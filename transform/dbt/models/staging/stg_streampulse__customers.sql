-- Names are not carried forward (data minimization). The email arrives as a SHA-256 hash of
-- the normalized address because dbt runs as TRANSFORMER (masking policy, ADR-003).
with source as (
    select * from {{ source('streampulse_raw', 'customers') }}
),

deduplicated as (
    select
        customer_id,
        email as email_hash,
        market_code,
        created_at,
        created_at::date as signup_date
    from source
    qualify row_number() over (
        partition by customer_id order by _loaded_at asc, _file_row_number asc
    ) = 1
)

select * from deduplicated
