# Stock-out policy

Likely stock-outs are products whose remaining inventory, at recent sales velocity, will not cover the next few selling days.

Formula:
average_daily_sales = recent_units / 14
inventory_coverage_days = current_stock / average_daily_sales

Prioritize:
1. Critical coverage (≤ 2 days) at high-velocity stores
2. High coverage risk (≤ 5 days) combined with stock below reorder level
3. Items that also show a recent sales increase, because demand may consume stock faster

If several products compete for attention, rank by severity first, then by estimated near-term revenue at risk (price × remaining demand). Confirm inbound purchase orders with operations before acting.
