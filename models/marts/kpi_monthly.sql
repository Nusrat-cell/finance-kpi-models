-- One row per month with the KPIs finance reviews every month end.
with revenue as (
    select invoice_month as month,
           sum(revenue_dkk) as revenue_dkk,
           sum(gross_profit_dkk) as gross_profit_dkk,
           count(distinct case when not is_credit_note then invoice_id end) as invoices
    from {{ ref('fct_invoice_lines') }}
    group by invoice_month
),
budget as (
    select month, sum(budget_revenue_dkk) as budget_revenue_dkk
    from {{ ref('stg_budget') }}
    group by month
),
-- Receivables at each month end, rebuilt from invoices and payments up to that
-- day. Payments are converted at the rate of the invoice they pay, so the
-- figure shows what is still owed, not exchange-rate gains or losses.
month_ends as (
    select month, date(month, '+1 month', '-1 day') as month_end from budget
),
invoice_rates as (
    select invoice_id, min(invoice_month) as invoice_month, min(currency) as currency
    from {{ ref('int_invoice_lines_dkk') }}
    group by invoice_id
),
payments_dkk as (
    select p.payment_date, p.amount * fx.dkk_per_unit as amount_dkk
    from {{ ref('stg_payments') }} p
    join invoice_rates r using (invoice_id)
    join {{ ref('stg_fx_rates') }} fx on fx.month = r.invoice_month and fx.currency = r.currency
),
ar as (
    select
        m.month,
        (select sum(revenue_dkk) from {{ ref('int_invoice_lines_dkk') }} where invoice_date <= m.month_end)
        - coalesce((select sum(amount_dkk) from payments_dkk where payment_date <= m.month_end), 0) as receivables_dkk
    from month_ends m
)
select
    b.month,
    round(coalesce(r.revenue_dkk, 0), 0)                                   as revenue_dkk,
    round(b.budget_revenue_dkk, 0)                                         as budget_revenue_dkk,
    round(100.0 * (coalesce(r.revenue_dkk, 0) - b.budget_revenue_dkk) / b.budget_revenue_dkk, 1) as budget_variance_pct,
    round(100.0 * r.gross_profit_dkk / nullif(r.revenue_dkk, 0), 1)        as gross_margin_pct,
    r.invoices,
    round(ar.receivables_dkk, 0)                                           as receivables_dkk,
    -- Days sales outstanding: receivables at month end / revenue of the month * days in month
    round(ar.receivables_dkk / nullif(r.revenue_dkk, 0)
          * cast(strftime('%d', date(b.month, '+1 month', '-1 day')) as integer), 0) as dso_days
from budget b
left join revenue r using (month)
left join ar using (month)
order by b.month
