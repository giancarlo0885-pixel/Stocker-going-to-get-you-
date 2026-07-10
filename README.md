# GARIBALDI MARKET ORACLE™ v2 — $10 Challenge

Two separate simulated $10 portfolios: a Cash Market Pit and a 24/7 Crypto Pit. Includes fractional paper trades, separate balances, persistent SQLite history, equity curves, confidence scores, headline-regime scoring, technical indicators, stop loss, take profit, trailing stop, slippage, and Railway deployment support.

## Railway
Set `PAPER_DB_PATH=/data/paper_trading.db` and mount a persistent volume at `/data`.

After deployment, reset both boards once inside the app if an older database still shows $100,000.

Educational paper trading only; no guarantees and no real orders.
