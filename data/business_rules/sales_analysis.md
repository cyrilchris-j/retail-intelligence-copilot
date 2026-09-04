# Sales analysis guidelines

Compare a recent 14-day window with the immediately preceding 14-day baseline.

change_percentage = ((recent - baseline) / baseline) × 100

- Spike if change ≥ +25%
- Drop if change ≤ -25%
- If baseline units are zero and recent units are also zero, history is insufficient
- If baseline units are zero and recent units are positive, percentage change is undefined; do not fabricate a percentage

Month-to-date figures use the first calendar day of the business month through the business date. Month-over-month compares that window with the previous full calendar month.

Sales changes are investigation flags. They are not automatic markdowns or forecasts.
