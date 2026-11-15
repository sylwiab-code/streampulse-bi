-- Latest version of each content_catalog row: the newest batch holds the current snapshot.
with source as (
    select * from {{ source('streampulse_raw', 'content_catalog') }}
),

latest as (
    select
        title_id,
        title_name,
        genre as genre_name,
        content_type,
        runtime_minutes,
        release_year,
        added_date,
        {{ load_date_from_file_name('_file_name') }} as load_date
    from source
    qualify row_number() over (
        partition by title_id order by load_date desc, _file_row_number asc
    ) = 1
)

select * from latest
