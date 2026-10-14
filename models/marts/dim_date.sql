-- A calendar covering every invoice and payment date, for Power BI's date table.
with recursive bounds as (
    select min(d) as first_day, max(d) as last_day from (
        select invoice_date as d from {{ ref('stg_invoice_lines') }}
        union all
        select payment_date from {{ ref('stg_payments') }}
    )
),
days(day) as (
    select date(first_day, 'start of month') from bounds
    union all
    select date(day, '+1 day') from days, bounds where day < date(last_day, 'start of month', '+1 month', '-1 day')
)
select
    day                                            as date,
    cast(strftime('%Y', day) as integer)           as year,
    cast(strftime('%m', day) as integer)           as month_number,
    date(day, 'start of month')                    as month_start,
    'Q' || ((cast(strftime('%m', day) as integer) + 2) / 3) as quarter,
    cast(strftime('%w', day) as integer) in (0, 6) as is_weekend
from days
