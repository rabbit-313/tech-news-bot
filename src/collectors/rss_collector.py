import feedparser
from datetime import datetime
from typing import List
import time

from .base_collector import BaseCollector
from ..models.article import Article
from ..utils.config import Config


class RSSCollector(BaseCollector):
    """RSS/Atom フィード収集クラス"""
    
    def __init__(self):
        super().__init__("rss")
        self.feeds = Config.RSS_FEEDS
    
    def collect(self) -> List[Article]:
        """RSSフィードから記事を収集"""
        all_articles = []
        
        for feed_config in self.feeds:
            try:
                self.logger.info(f"Fetching RSS feed: {feed_config['url']}")
                articles = self._collect_from_feed(feed_config)
                all_articles.extend(articles)
                self.logger.info(f"Collected {len(articles)} articles from {feed_config['source']}")
                
                # API制限対策で少し待機
                time.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Failed to fetch RSS feed {feed_config['url']}: {e}")
        
        return all_articles
    
    def _collect_from_feed(self, feed_config: dict) -> List[Article]:
        """個別のRSSフィードから記事を収集"""
        articles = []
        
        try:
            feed = feedparser.parse(feed_config["url"])
            
            if feed.bozo:
                self.logger.warning(f"Feed may have issues: {feed_config['url']}")
            
            for entry in feed.entries:
                try:
                    published_time = self._parse_published_time(entry)
                    
                    # 古い記事は除外
                    if not self._is_recent(published_time, Config.HOURS_LOOKBACK):
                        continue
                    
                    # 記事の概要を取得
                    summary = self._extract_summary(entry)
                    
                    # スコア計算
                    score = self._calculate_score(
                        title=entry.title,
                        summary=summary
                    )
                    
                    # タグ抽出
                    tags = self._extract_tags(entry.title, summary)
                    
                    article = Article(
                        title=self._clean_text(entry.title),
                        url=entry.link,
                        summary=self._clean_text(summary),
                        published_at=published_time,
                        source=feed_config["source"],
                        tags=tags,
                        score=score,
                        content_hash="",  # __post_init__で生成される
                        author=self._extract_author(entry)
                    )
                    
                    articles.append(article)
                    
                except Exception as e:
                    self.logger.error(f"Failed to parse entry from {feed_config['source']}: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Failed to parse feed {feed_config['url']}: {e}")
        
        return articles
    
    def _parse_published_time(self, entry) -> datetime:
        """エントリの公開時刻をパース"""
        # published_parsed が利用可能な場合
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            return datetime(*entry.published_parsed[:6])
        
        # updated_parsed を代替として使用
        if hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            return datetime(*entry.updated_parsed[:6])
        
        # パースできない場合は現在時刻を使用
        self.logger.warning(f"Could not parse publish time for: {entry.get('title', 'Unknown')}")
        return datetime.now()
    
    def _extract_summary(self, entry) -> str:
        """エントリから概要を抽出"""
        # summary が利用可能な場合
        if hasattr(entry, 'summary') and entry.summary:
            return entry.summary
        
        # description を代替として使用
        if hasattr(entry, 'description') and entry.description:
            return entry.description
        
        # content を使用
        if hasattr(entry, 'content') and entry.content:
            if isinstance(entry.content, list) and len(entry.content) > 0:
                return entry.content[0].get('value', '')
            return str(entry.content)
        
        return ""
    
    def _extract_author(self, entry) -> str:
        """エントリから著者を抽出"""
        if hasattr(entry, 'author') and entry.author:
            return entry.author
        
        if hasattr(entry, 'authors') and entry.authors:
            if isinstance(entry.authors, list) and len(entry.authors) > 0:
                return entry.authors[0].get('name', '')
        
        return None