select
    date(month)                 as month,
    upper(currency)             as currency,
    cast(dkk_per_unit as real)  as dkk_per_unit
from {{ ref('fx_monthly_rates') }}
