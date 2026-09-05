# Stock-out policy

Likely stock-outs are products whose remaining inventory, at recent sales velocity, will not cover the next few selling days.

Formula:
average_daily_sales = recent_units / 14
inventory_coverage_days = current_stock / average_daily_sales

Classification by coverage days (exact thresholds):
- Critical: coverage ≤ 2 days
- High: coverage > 2 and ≤ 5 days
- Medium: coverage > 5 and ≤ 7 days
- Not a stock-out risk: coverage > 7 days, even when stock is below the reorder level

When stock is at or below the reorder level but coverage is above 7 days, flag it as a replenishment review signal instead of a stock-out risk. The two signals are separate.

Prioritize critical and high coverage at high-velocity stores first, then medium. If several products compete for attention, rank by severity first, then by estimated near-term revenue at risk (price × remaining demand). Confirm inbound purchase orders with operations before acting.