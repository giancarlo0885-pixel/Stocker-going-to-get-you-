# Deployment checklist

1. Upload all files to the root of the original GitHub repository.
2. Replace old files when GitHub asks.
3. Confirm the root contains:
   - `app.py`
   - `engine.py`
   - `market_data.py`
   - `market_predictor.py`
   - `news_intelligence.py`
   - `risk_engine.py`
   - `oracle_bot.py`
   - `oracle_worker.py`
   - `api_manager.py`
   - `config.py`
   - `db.py`
   - `start.sh`
   - `Procfile`
   - `requirements.txt`
4. Commit changes.
5. Open Railway and wait for deployment.
6. Check deployment logs for:
   - `Starting GARIBALDI MARKET ORACLE`
   - `Launching background worker`
   - `Worker started`
   - `Beginning scan`
7. Open the website.
8. Add `OPENAI_API_KEY` and `FINNHUB_API_KEY` only in Railway Variables.
9. Add Railway PostgreSQL for permanent storage.
10. Never paste private API keys into GitHub.
