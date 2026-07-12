from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import re

import feedparser

from api_manager import request_json
from config import settings


@dataclass(frozen=True)
class NewsItem:
    headline: str
    source: str
    url: str
    published_at: str
    sentiment: str
    score: int
    summary: str


POSITIVE = {
    "beat", "growth", "surge", "gain", "record", "approval", "partnership",
    "profit", "upgrade", "bullish", "expansion", "strong", "rally", "adoption",
}
NEGATIVE = {
    "miss", "loss", "drop", "decline", "lawsuit", "investigation", "downgrade",
    "bearish", "warning", "fraud", "ban", "weak", "recession", "default", "hack",
}


def score_text(text: str) -> tuple[str, int]:
    words = set(re.findall(r"[a-zA-Z]+", text.lower()))
    raw = len(words & POSITIVE) - len(words & NEGATIVE)
    score = max(0, min(100, 50 + raw * 10))
    label = "Positive" if score > 55 else "Negative" if score < 45 else "Neutral"
    return label, score


def _finnhub_news(symbol: str, limit: int) -> list[NewsItem]:
    if not settings.finnhub_api_key:
        return []

    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=7)
    payload = request_json(
        "https://finnhub.io/api/v1/company-news",
        params={
            "symbol": symbol.upper(),
            "from": start.isoformat(),
            "to": today.isoformat(),
            "token": settings.finnhub_api_key,
        },
    )

    items = []
    for row in payload[:limit]:
        headline = row.get("headline", "Untitled")
        summary = row.get("summary", "")
        sentiment, score = score_text(f"{headline} {summary}")
        items.append(NewsItem(
            headline=headline,
            source=row.get("source", "Finnhub"),
            url=row.get("url", ""),
            published_at=str(row.get("datetime", "")),
            sentiment=sentiment,
            score=score,
            summary=summary,
        ))
    return items


def _google_news(symbol: str, limit: int) -> list[NewsItem]:
    query = symbol.replace(" ", "+")
    feed = feedparser.parse(
        f"https://news.google.com/rss/search?q={query}+market&hl=en-US&gl=US&ceid=US:en"
    )
    items = []
    for entry in feed.entries[:limit]:
        headline = entry.get("title", "Untitled")
        raw_summary = entry.get("summary", "")
        summary = re.sub("<[^>]+>", "", raw_summary)
        sentiment, score = score_text(f"{headline} {summary}")
        source_data = entry.get("source")
        source = source_data.get("title", "Google News") if isinstance(source_data, dict) else "Google News"
        items.append(NewsItem(
            headline=headline,
            source=source,
            url=entry.get("link", ""),
            published_at=entry.get("published", ""),
            sentiment=sentiment,
            score=score,
            summary=summary,
        ))
    return items


def get_market_news(symbol: str, limit: int = 8) -> list[NewsItem]:
    try:
        items = _finnhub_news(symbol, limit)
        if items:
            return items
    except Exception:
        pass
    try:
        return _google_news(symbol, limit)
    except Exception:
        return []


def aggregate_news_sentiment(symbol: str, limit: int = 8) -> dict:
    items = get_market_news(symbol, limit)
    if not items:
        return {"symbol": symbol.upper(), "sentiment": "Neutral", "score": 50, "count": 0, "items": []}

    score = round(sum(x.score for x in items) / len(items))
    sentiment = "Positive" if score > 55 else "Negative" if score < 45 else "Neutral"
    return {"symbol": symbol.upper(), "sentiment": sentiment, "score": score, "count": len(items), "items": items}
