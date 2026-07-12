# GARIBALDI MARKET ORACLE™

A beginner-friendly Streamlit application for:

- Stocks and ETFs
- Crypto
- Fiat currency conversion
- Historical-pattern forecasts
- News sentiment
- Risk analysis
- $10 automated paper-trading boards
- Optional AI explanations
- Railway deployment with a supervised 24/7 worker

## Drop-in installation

Upload every file in this repository to the root of your GitHub repository and replace the old versions.

Railway should redeploy automatically.

## Required Railway variables

None are strictly required for basic operation.

Recommended:

```text
FINNHUB_API_KEY=...
OPENAI_API_KEY=...
BOT_SCAN_SECONDS=300
```

For permanent storage, add Railway PostgreSQL. Railway will normally inject `DATABASE_URL`.

Without PostgreSQL, the app falls back to SQLite. SQLite data can be lost during redeployment unless a persistent volume is mounted.

## Start process

`Procfile` runs:

```text
web: bash start.sh
```

`start.sh` launches both:

- `oracle_worker.py`
- Streamlit `app.py`

It also restarts the worker if it exits.

## Safety design

- Paper trading only
- Position-size limits
- Maximum open positions
- Confidence labels
- Risk reports
- Forecast ranges instead of guaranteed targets
- No real brokerage integration
- No promises of profit

## Local run

```bash
pip install -r requirements.txt
streamlit run app.py
```

In another terminal:

```bash
python oracle_worker.py
```

## Important

Market prices, news feeds and third-party APIs can fail or become temporarily unavailable. Forecasts are statistical estimates and can be wrong.
