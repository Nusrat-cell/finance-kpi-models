-- A monthly gross margin outside 0..90 % means a cost or price is wrong
-- (for example a standard cost entered in DKK instead of EUR).
select month, gross_margin_pct
from {{ ref('kpi_monthly') }}
where gross_margin_pct is not null
  and (gross_margin_pct < 0 or gross_margin_pct > 90)
