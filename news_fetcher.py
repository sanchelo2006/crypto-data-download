"""
Модуль для получения и суммаризации крипто-новостей через RSS-ленты.
"""

import requests
import pandas as pd
import feedparser
from transformers import pipeline
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NewsAggregator:
    RSS_FEEDS = {
        "beincrypto": "https://beincrypto.com/feed",
        "binance_blog": "https://www.binance.com/en/blog/feed",
        "bitcoin_com_news": "https://news.bitcoin.com/feed/",
        "bitfinex_blog": "https://blog.bitfinex.com/feed/",
        "blockworks": "https://blockworks.co/rss",
        "coindesk": "https://www.coindesk.com/arc/outboundfeeds/rss",
        "coingape": "https://coingape.com/feed/",
        "coingecko_learn": "https://www.coingecko.com/learn/feed",
        "cointelegraph": "https://cointelegraph.com/rss",
        "crypto_briefing": "https://cryptobriefing.com/feed/",
        "cryptopanic": "https://cryptopanic.com/api/v2/posts/?format=rss",
        "cryptoslate": "https://cryptoslate.com/feed/",
        "decrypt": "https://decrypt.co/feed",
        "kucoin_blog": "https://www.kucoin.com/blog/rss.xml",
        "newsbtc": "https://www.newsbtc.com/feed/",
        "the_block": "https://www.theblock.co/rss",
        "u_today": "https://u.today/rss",
    }

    def __init__(self, lunarcrush_key: Optional[str] = None):
        self.lunarcrush_key = lunarcrush_key
        self.summarizer = None
        if not self.lunarcrush_key:
            logger.info("Loading local Hugging Face model...")
            try:
                self.summarizer = pipeline("summarization", model="bpavlsh/bart-crypto-summary")
                logger.info("Local model loaded.")
            except Exception as e:
                logger.error(f"Failed to load model: {e}")

    def fetch_articles_from_feeds(self, limit: int = 50) -> List[Dict]:
        articles = []
        for source_name, feed_url in self.RSS_FEEDS.items():
            try:
                logger.info(f"Parsing RSS feed: {source_name}")
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:limit]:
                    articles.append({
                        "date": entry.get("published", datetime.now().isoformat()),
                        "title": entry.get("title", "No Title"),
                        "summary": entry.get("summary", ""),
                        "url": entry.get("link", ""),
                        "source": source_name
                    })
            except Exception as e:
                logger.error(f"Failed to parse {source_name}: {e}")
        return articles

    def filter_articles_by_symbol(self, articles: List[Dict], coin_symbol: str) -> List[Dict]:
        coin_lower = coin_symbol.lower()
        return [a for a in articles if coin_lower in a["title"].lower()]

    def _parse_date(self, date_val) -> datetime:
        """Преобразует дату из RSS в наивный datetime (без часового пояса)."""
        # Если это уже datetime-объект
        if isinstance(date_val, datetime):
            # Если он с часовым поясом – удаляем его
            if date_val.tzinfo is not None:
                return date_val.replace(tzinfo=None)
            return date_val
        # Пытаемся распарсить строку
        try:
            from dateutil import parser
            dt = parser.parse(date_val)
            if dt.tzinfo is not None:
                return dt.replace(tzinfo=None)
            return dt
        except Exception:
            # Если не получилось, возвращаем текущее время (без часового пояса)
            return datetime.now()

    def summarize_locally(self, text: str) -> str:
        if not self.summarizer:
            return "Summarization model not available."
        try:
            max_len = 1024
            if len(text) > max_len:
                text = text[:max_len]
            summary = self.summarizer(text, max_length=130, min_length=30, do_sample=False)[0]['summary_text']
            return summary
        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            return text[:200] + "..."

    def fetch_news(self, coin_symbol: str, source: str = "rss", limit: int = 20, max_age_days: int = 30) -> pd.DataFrame:
        articles = self.fetch_articles_from_feeds(limit=limit * 2)
        if not articles:
            return pd.DataFrame()

        filtered = self.filter_articles_by_symbol(articles, coin_symbol)
        if max_age_days is not None:
            cutoff = datetime.now() - timedelta(days=max_age_days)  # наивная дата
            filtered = [a for a in filtered if self._parse_date(a.get("date")) >= cutoff]

        if not filtered:
            return pd.DataFrame()

        data = []
        for article in filtered[:limit]:
            text_to_summarize = article.get("summary", article["title"])
            summary = self.summarize_locally(text_to_summarize) if self.summarizer else (text_to_summarize[:200] + "...")
            data.append({
                "date": article.get("date", "N/A"),
                "title": article["title"],
                "summary": summary,
                "url": article.get("url", "N/A"),
                "source": article.get("source", "N/A")
            })
        return pd.DataFrame(data)