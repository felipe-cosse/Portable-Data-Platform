select
    toInt64(event_id) as event_id,
    toInt64(customer_id) as customer_id,
    event_name,
    occurred_at
from {{ source('local_demo', 'events') }}
