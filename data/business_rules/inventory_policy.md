# Inventory policy

Inventory coverage is current_stock divided by average daily sales over the last 14 days, ending on the business date.

Stock-out risk:
- Critical: coverage ≤ 2 days
- High: coverage ≤ 5 days
- Medium: coverage ≤ 7 days, or current stock at or below reorder level
- If average daily sales are zero, coverage is undefined. Do not invent a coverage figure. Flag medium risk only when stock is also at or below reorder level.

Fast-selling items can have high absolute stock and still be healthy. Do not treat high stock alone as a problem.

Replenishment recommendations are for the manager to consider. The copilot never places purchase orders or changes inventory records.
