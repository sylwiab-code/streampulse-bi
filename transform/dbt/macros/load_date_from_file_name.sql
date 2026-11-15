{#- The loader stages files as <table>/load_date=YYYY-MM-DD/...;
    RAW keeps the path in _file_name. -#}
{% macro load_date_from_file_name(column_name) -%}
    to_date(regexp_substr({{ column_name }}, 'load_date=([0-9]{4}-[0-9]{2}-[0-9]{2})', 1, 1, 'e'))
{%- endmacro %}
