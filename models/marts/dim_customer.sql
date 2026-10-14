select customer_id, customer_name, country, segment, payment_terms_days
from {{ ref('stg_customers') }}
