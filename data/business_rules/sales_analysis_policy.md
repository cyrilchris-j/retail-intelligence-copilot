# Sales analysis policy

Compare a recent 14-day window with the immediately preceding 14-day baseline.

change_percentage = ((recent - baseline) / baseline) × 100

- Spike if change ≥ +25%
- Drop if change ≤ -25%
- If baseline units are zero and recent units are also zero, history is insufficient
- If baseline units are zero and recent units are positive, percentage change is undefined; do not fabricate a percentage

Month-to-date figures use the first calendar day of the business month through the business date. Month-over-month compares equal-length windows: the MTD days so far this month versus the same calendar days of the previous month (for example September 1-4 versus August 1-4), never a partial month against a full month. If the comparison window has no sales, state that no comparable baseline exists.

Sales changes are investigation flags. They are not automatic markdowns or forecasts.