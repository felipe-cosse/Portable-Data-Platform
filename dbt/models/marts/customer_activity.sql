with customers as (
    select * from {{ ref('stg_customers') }}
),
events as (
    select
        customer_id,
        count() as event_count,
        max(occurred_at) as last_event_at
    from {{ ref('stg_events') }}
    group by customer_id
),
orders as (
    select
        customer_id,
        count() as order_count,
        sum(amount) as lifetime_value,
        max(ordered_at) as last_order_at
    from {{ ref('stg_orders') }}
    group by customer_id
)
select
    customers.customer_id as customer_id,
    customers.name,
    customers.segment,
    coalesce(events.event_count, 0) as event_count,
    events.last_event_at,
    coalesce(orders.order_count, 0) as order_count,
    coalesce(orders.lifetime_value, toDecimal64(0, 2)) as lifetime_value,
    orders.last_order_at
from customers
left join events using (customer_id)
left join orders using (customer_id)
