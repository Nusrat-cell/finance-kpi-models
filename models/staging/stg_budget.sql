select
    date(month)                       as month,
    product_line,
    cast(budget_revenue_dkk as real)  as budget_revenue_dkk
from {{ ref('budget_monthly') }}
