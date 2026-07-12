# GARIBALDI MARKET ORACLE — Add-On Upgrade Pack

Upload every file in this ZIP to the root of the existing GitHub repository.

This pack adds:

- Economic calendar
- Earnings calendar
- Backtesting
- Portfolio statistics
- Market regime detection
- Data-quality checks
- Deduplicated SQLite alerts
- Railway worker heartbeat
- Optional supervised 24/7 intelligence worker

It does **not** place real-money orders. Forecasts are uncertain and should be
shown as probabilities or scenarios, not guaranteed future prices.

## Quick installation

1. Upload all `.py` files to the repository root.
2. Add the lines from `requirements_additions.txt` to the existing
   `requirements.txt` without deleting the old lines.
3. Follow `ADD_TO_APP.md` to display the new panels.
4. Create a second Railway service with the command in
   `RAILWAY_WORKER_COMMAND.txt`.
5. Add a persistent volume mounted at `/data`.
6. Add `FINNHUB_API_KEY` in Railway Variables.
