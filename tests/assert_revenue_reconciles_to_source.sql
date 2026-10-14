-- Total revenue in the fact table must equal the source lines converted at
-- the month rate, after removing the duplicated export line. Catches joins
-- that drop or multiply rows.
with source as (
    select sum(cast(l.quantity as real) * cast(l.unit_price as real) * fx.dkk_per_unit) as total
    from (select distinct * from {{ ref('erp_invoice_lines') }}) l
    join {{ ref('stg_fx_rates') }} fx
      on fx.month = date(l.invoice_date, 'start of month') and fx.currency = l.currency
),
mart as (
    select sum(revenue_dkk) as total from {{ ref('fct_invoice_lines') }}
)
select source.total, mart.total
from source, mart
where abs(source.total - mart.total) > 1
