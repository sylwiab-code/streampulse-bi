with titles as (
    select * from {{ ref('stg_streampulse__content_catalog') }}
),

final as (
    select
        title_id::number(38, 0) as title_id,
        title_name::varchar as title_name,
        genre_name::varchar as genre_name,
        content_type::varchar as content_type,
        runtime_minutes::number(38, 0) as runtime_minutes,
        release_year::number(38, 0) as release_year,
        added_date::date as added_date
    from titles
)

select * from final
