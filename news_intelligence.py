from __future__ import annotations
from dataclasses import dataclass
from urllib.parse import quote_plus
import feedparser
import pandas as pd

QUERIES = {
    "cash":"stocks bonds dollar Federal Reserve earnings global market",
    "crypto":"bitcoin ethereum crypto regulation ETF global market",
}
RISK = {"war","attack","sanction","tariff","recession","default","crisis","collapse","fraud","hack","ban","inflation","layoffs","missile"}
POS = {"growth","rally","approval","cut","deal","surge","record","expansion","profit","upgrade","adoption","ceasefire"}

@dataclass
class NewsRegime:
    score: float
    label: str
    explanation: str
    headlines: pd.DataFrame

def fetch_news(topic: str, limit: int = 20) -> pd.DataFrame:
    q = QUERIES.get(topic, topic)
    url = "https://news.google.com/rss/search?q=" + quote_plus(q) + "&hl=en-US&gl=US&ceid=US:en"
    feed = feedparser.parse(url)
    rows = []
    for e in feed.entries[:limit]:
        rows.append({"published":e.get("published",""),"title":e.get("title",""),"link":e.get("link",""),"source":(e.get("source") or {}).get("title","Google News")})
    return pd.DataFrame(rows)

def combined_regime(topic: str) -> NewsRegime:
    x = fetch_news(topic)
    if x.empty:
        return NewsRegime(0.0,"Neutral","No current headlines were available, so news is not changing position size.",x)
    raw = 0
    for title in x["title"].fillna("").astype(str):
        words = {w.strip(".,:;!?()[]{}'\"").lower() for w in title.split()}
        raw += len(words & POS) - len(words & RISK)
    score = max(-1.0, min(1.0, raw / max(6, len(x)*0.35)))
    if score <= -0.35:
        return NewsRegime(score,"Risk-off","Headlines contain elevated geopolitical, inflation, recession, or policy-risk language.",x)
    if score >= 0.35:
        return NewsRegime(score,"Risk-on","Headlines contain more growth, easing, deal, approval, and rally language.",x)
    return NewsRegime(score,"Mixed","Headline signals are balanced or inconclusive.",x)
