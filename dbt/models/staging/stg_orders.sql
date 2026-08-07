select
    toInt64(order_id) as order_id,
    toInt64(customer_id) as customer_id,
    toDecimal64(amount, 2) as amount,
    parseDateTimeBestEffort(toString(ordered_at)) as ordered_at
from {{ source('local_demo', 'orders') }}
