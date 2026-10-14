-- The fact table for revenue and margin, at invoice line grain.
select
    i.invoice_id || '-' || i.line_no as invoice_line_key,
    i.invoice_id,
    i.line_no,
    i.invoice_date,
    i.invoice_month,
    i.customer_id,
    i.product_id,
    p.product_line,
    i.quantity,
    i.currency,
    i.is_credit_note,
    i.revenue_dkk,
    i.cogs_dkk,
    i.revenue_dkk - i.cogs_dkk as gross_profit_dkk
from {{ ref('int_invoice_lines_dkk') }} i
join {{ ref('stg_products') }} p using (product_id)
