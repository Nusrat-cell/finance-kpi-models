select
    b.month,
    b.product_line,
    round(coalesce(sum(f.revenue_dkk), 0), 0)                                          as revenue_dkk,
    round(b.budget_revenue_dkk, 0)                                                     as budget_revenue_dkk,
    round(100.0 * (coalesce(sum(f.revenue_dkk), 0) - b.budget_revenue_dkk) / b.budget_revenue_dkk, 1) as budget_variance_pct,
    round(100.0 * sum(f.gross_profit_dkk) / nullif(sum(f.revenue_dkk), 0), 1)          as gross_margin_pct
from {{ ref('stg_budget') }} b
left join {{ ref('fct_invoice_lines') }} f
    on f.invoice_month = b.month and f.product_line = b.product_line
group by b.month, b.product_line, b.budget_revenue_dkk
order by b.month, b.product_line
