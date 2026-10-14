select
    customer_id,
    customer_name,
    country,
    segment,
    cast(payment_terms_days as integer) as payment_terms_days
from {{ ref('erp_customers') }}
