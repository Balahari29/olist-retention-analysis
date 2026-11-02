# Process Map: Order-to-Review (as-is), steps for draw.io
**Version:** 0.1 (draft, Phase 1) | **Date:** 2026-11-02
**Save as:** `docs/04_process_map.drawio` + export `docs/04_process_map.png`

## How to draw it
- **Layout:** horizontal swimlane diagram (draw.io → *Arrange → Insert → Horizontal Pool*), 4 lanes, top to bottom:
  **Customer | Olist Platform | Seller | Carrier**.
- **Shapes:** rounded rectangle = step, diamond = decision, oval = start/end, a small grey note = the data column
  that records the step (this is what links the business process to our data).
- Flow runs left → right. Number the steps as below.

## Steps
| # | Lane | Shape | Step | Data captured (table.column) |
|---|---|---|---|---|
| S | Customer | Oval | **Start:** customer places order on a marketplace store | `orders.order_purchase_timestamp` |
| 1 | Customer | Rectangle | Pays for the order (card, boleto, voucher, debit) | `order_payments.payment_type`, `payment_value` |
| 2 | Olist Platform | Diamond | **Payment approved?** | `orders.order_approved_at` |
| 2a | Olist Platform | Oval | *No* → **End: order canceled / unavailable** | `orders.order_status` = `canceled` / `unavailable` |
| 3 | Olist Platform | Rectangle | *Yes* → calculates estimated delivery date, shows it to customer, notifies seller | `orders.order_estimated_delivery_date` |
| 4 | Seller | Rectangle | Prepares and packs the items | `order_items.shipping_limit_date` (deadline to hand over) |
| 5 | Seller | Rectangle | Hands package to carrier | `orders.order_delivered_carrier_date` |
| 6 | Carrier | Rectangle | Transports package to customer's city/state | `sellers.seller_state` → `customers.customer_state` |
| 7 | Carrier | Rectangle | Delivers package to customer | `orders.order_delivered_customer_date` |
| 8 | Olist Platform | Diamond | **Delivered on or before estimated date?** (Delay ≤ 0) | Delay = delivered date − estimated date |
| 8a | Olist Platform | Rectangle | *Yes* → counts as **On time** | On-Time Delivery % |
| 8b | Olist Platform | Rectangle | *No* → counts as **Late** (bucket 1–3 / 4–7 / 7+ days) | Late Order %, Avg Delivery Delay |
| 9 | Olist Platform | Rectangle | Sends satisfaction survey to customer | `order_reviews.review_creation_date` |
| 10 | Customer | Rectangle | Gives review score (1–5) and optional comment | `order_reviews.review_score`, `review_answer_timestamp` |
| 11 | Customer | Diamond | **Buys again later?** | Next order with same `customers.customer_unique_id` |
| 11a | Customer | Oval | *Yes* → **End: repeat customer** (loops back to Start) | Repeat Customer %, Cohort Retention % |
| 11b | Customer | Oval | *No* → **End: one-time customer** | — |

## Pain points to highlight on the map (red callouts)
1. **Between steps 4 and 5:** late hand-over by the seller (carrier date after `shipping_limit_date`). Feeds US-03.
2. **Step 6:** long distance between seller and customer state may cause delay. Tested in Phase 4 (haversine distance).
3. **Step 8b → 10:** a late delivery may lead to a lower review score. Tested in US-02 (hypothesis test).
4. **Step 10 → 11:** a low review may stop the customer buying again. Link to retention (US-01).

> Steps 3 and 9 (how Olist sets estimated dates and when the survey is sent) are inferred from the column names
> and the Kaggle dataset description; check the timestamp order in Phase 2 before presenting the map as fact.
