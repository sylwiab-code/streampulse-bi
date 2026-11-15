{#- Use the configured schema name as is (STAGING, MARTS, ...): the schemas are created by
    Liquibase with managed access (ADR-003), so dbt must not invent prefixed names. -#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
