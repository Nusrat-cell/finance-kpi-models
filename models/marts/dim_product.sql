select product_id, product_name, product_line, standard_cost_eur, list_price_eur
from {{ ref('stg_products') }}
