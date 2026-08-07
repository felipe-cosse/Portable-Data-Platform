select
    toInt64(customer_id) as customer_id,
    name,
    segment,
    created_at
from {{ source('local_demo', 'customers') }}
