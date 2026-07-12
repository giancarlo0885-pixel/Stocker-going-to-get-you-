# Add the API keys safely

## 1. Get the keys

Create accounts with the providers you plan to use:

- Finnhub: stock quotes, company information, and news.
- Alpha Vantage: economic indicators, stocks, forex, and crypto.
- Polygon/Massive: options snapshots. Options access may require a paid plan.

You do not need every key for the app to start. A feature will show a clear
"missing variable" message when its key is absent.

## 2. Put keys in Railway — not GitHub

For the web service:

1. Open the Railway project.
2. Tap the web service box.
3. Open **Variables**.
4. Tap **New Variable**.
5. Add each name and paste its matching secret value:

```
FINNHUB_API_KEY
ALPHA_VANTAGE_API_KEY
POLYGON_API_KEY
ORACLE_WORKER_INTERVAL_SECONDS
```

Use `300` for `ORACLE_WORKER_INTERVAL_SECONDS` to run a cycle every five
minutes. Save the variables and redeploy.

Repeat the variables on the worker service, or use Railway shared variables if
both services should receive the same keys.

## 3. Worker command

Create a second Railway service from the same GitHub repository and set its
start command to:

```
python enhanced_worker.py
```

The web service start command remains:

```
streamlit run app.py --server.address 0.0.0.0 --server.port $PORT
```

## 4. Requirements

Open your existing `requirements.txt` and add these lines if they are missing:

```
requests>=2.32,<3
streamlit>=1.42,<2
```

Do not replace the rest of your existing requirements.

## 5. Add the screen to the app

Open `app_addons_example.py`. Copy the sections you want into the bottom of
your existing `app.py`. The example imports the options scanner, economic
data, confidence score, and paper-trade journal.

## Security rules

- Never paste a real key into GitHub, README, app.py, screenshots, or chat.
- Do not commit a `.env` file containing real keys.
- If a key is exposed, revoke it at the provider and create a new one.
- These modules provide research and paper-trading tools only; predictions are
  uncertain and are not guaranteed profits.
