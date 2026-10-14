-- One row per invoice line. The ERP export sometimes repeats a line, so
-- duplicates on (invoice_id, line_no) are removed here, keeping the first.
with ranked as (
    select
        *,
        row_number() over (partition by invoice_id, line_no order by rowid) as copy_no
    from {{ ref('erp_invoice_lines') }}
)
select
    invoice_id,
    cast(line_no as integer)                 as line_no,
    date(invoice_date)                       as invoice_date,
    date(invoice_date, 'start of month')     as invoice_month,
    date(due_date)                           as due_date,
    customer_id,
    product_id,
    cast(quantity as integer)                as quantity,
    cast(unit_price as real)                 as unit_price,
    upper(currency)                          as currency,
    invoice_id like 'CRN%'                   as is_credit_note
from ranked
where copy_no = 1
