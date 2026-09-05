# Inventory policy

Inventory coverage is current_stock divided by average daily sales over the last 14 days, ending on the business date.

Stock-out risk by coverage days:
- Critical: coverage ≤ 2 days
- High: coverage > 2 and ≤ 5 days
- Medium: coverage > 5 and ≤ 7 days
- Not a stock-out risk: coverage > 7 days

Stock at or below the reorder level does not change the coverage classification. Below-reorder items with coverage above 7 days are a separate replenishment-review signal, never a stock-out label.

If average daily sales are zero, coverage is undefined. Do not invent a coverage figure. Flag medium risk only when stock is also at or below the reorder level.

Fast-selling items can have high absolute stock and still be healthy. Do not treat high stock alone as a problem.

Replenishment recommendations are for the manager to consider. The copilot never places purchase orders or changes inventory records.