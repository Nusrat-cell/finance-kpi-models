select
    product_id,
    product_name,
    product_line,
    cast(standard_cost_eur as real) as standard_cost_eur,
    cast(list_price_eur as real)    as list_price_eur
from {{ ref('erp_products') }}
