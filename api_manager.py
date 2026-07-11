import os
import pandas as pd

def provider_status_frame():
    return pd.DataFrame([
        {"Provider":"Finnhub","Variable":"FINNHUB_API_KEY","Connected":bool(os.getenv("FINNHUB_API_KEY"))},
        {"Provider":"Polygon","Variable":"POLYGON_API_KEY","Connected":bool(os.getenv("POLYGON_API_KEY"))},
        {"Provider":"Financial Modeling Prep","Variable":"FMP_API_KEY","Connected":bool(os.getenv("FMP_API_KEY"))},
        {"Provider":"NewsAPI","Variable":"NEWS_API_KEY","Connected":bool(os.getenv("NEWS_API_KEY"))},
    ])

def get_oracle_data_bundle(symbol):
    return {
        "profile":{},
        "analyst":{},
        "insiders":{},
        "earnings":{},
        "fundamentals":{},
        "news":[],
        "sources":{}
    }
