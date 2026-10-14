-- Paying more than was invoiced (or counting a payment twice) shows up as a
-- negative open amount.
select invoice_id, open_dkk
from {{ ref('fct_receivables') }}
where open_dkk < -0.01
