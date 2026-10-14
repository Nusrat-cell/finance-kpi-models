-- Accounts receivable per invoice at the reporting date (30 September 2026).
-- Payments are summed first, because one invoice can be paid in instalments;
-- joining payments straight onto invoice lines would multiply the rows.
with invoices as (
    select invoice_id, customer_id, min(invoice_date) as invoice_date, min(due_date) as due_date,
           min(currency) as currency, sum(amount_local) as invoiced_local, sum(revenue_dkk) as invoiced_dkk
    from {{ ref('int_invoice_lines_dkk') }}
    where not is_credit_note
    group by invoice_id, customer_id
),
paid as (
    select invoice_id, sum(amount) as paid_local, max(payment_date) as last_payment_date
    from {{ ref('stg_payments') }}
    where payment_date <= '2026-09-30'
    group by invoice_id
)
select
    i.invoice_id,
    i.customer_id,
    i.invoice_date,
    i.due_date,
    i.currency,
    i.invoiced_dkk,
    round(i.invoiced_dkk * (1 - coalesce(p.paid_local, 0) / i.invoiced_local), 2) as open_dkk,
    p.last_payment_date,
    case
        when coalesce(p.paid_local, 0) >= i.invoiced_local - 0.01 then 'Paid'
        when '2026-09-30' > i.due_date then 'Overdue'
        else 'Open'
    end as status,
    max(0, cast(julianday('2026-09-30') - julianday(i.due_date) as integer)) as days_past_due
from invoices i
left join paid p using (invoice_id)
