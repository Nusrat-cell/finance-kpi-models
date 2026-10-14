-- An invoice paid in two instalments must appear once, fully paid.
select invoice_id
from {{ ref('fct_receivables') }}
where invoice_id in (
    select invoice_id from {{ ref('stg_payments') }} group by invoice_id having count(*) > 1
)
and status <> 'Paid'
