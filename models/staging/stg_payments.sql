select
    payment_id,
    invoice_id,
    date(payment_date)      as payment_date,
    cast(amount as real)    as amount,
    upper(currency)         as currency
from {{ ref('erp_payments') }}
