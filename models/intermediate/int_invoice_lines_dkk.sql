-- Converts every line to DKK at the average rate of the invoice month, and
-- adds the cost of goods sold from the product's standard cost (kept in EUR).
-- An inner join on the rate would silently drop lines in a currency with no
-- rate; a left join plus the not_null test on revenue_dkk makes that loud.
select
    l.invoice_id,
    l.line_no,
    l.invoice_date,
    l.invoice_month,
    l.due_date,
    l.customer_id,
    l.product_id,
    l.quantity,
    l.currency,
    l.is_credit_note,
    l.quantity * l.unit_price                                      as amount_local,
    round(l.quantity * l.unit_price * fx.dkk_per_unit, 2)          as revenue_dkk,
    round(l.quantity * p.standard_cost_eur * eur.dkk_per_unit, 2)  as cogs_dkk
from {{ ref('stg_invoice_lines') }} l
left join {{ ref('stg_fx_rates') }} fx
    on fx.month = l.invoice_month and fx.currency = l.currency
left join {{ ref('stg_fx_rates') }} eur
    on eur.month = l.invoice_month and eur.currency = 'EUR'
left join {{ ref('stg_products') }} p
    on p.product_id = l.product_id
