from typing import List

from ..models.article import Article
from .deduplicator import Deduplicator
from .content_filter import ContentFilter
from ..utils.logger import setup_logger


class ArticleProcessor:
    """記事処理の統合クラス"""
    
    def __init__(self):
        self.logger = setup_logger("article_processor")
        self.deduplicator = Deduplicator()
        self.content_filter = ContentFilter()
    
    def process(self, articles: List[Article]) -> List[Article]:
        """記事の総合的な処理"""
        self.logger.info(f"Starting article processing with {len(articles)} articles")
        
        # 1. 重複除去
        unique_articles = self.deduplicator.remove_duplicates(articles)
        
        # 2. コンテンツフィルタリング
        filtered_articles = self.content_filter.filter(unique_articles)
        
        # 3. スコアベースソート
        sorted_articles = sorted(filtered_articles, key=lambda x: x.score, reverse=True)
        
        self.logger.info(f"Article processing completed: {len(sorted_articles)} articles")
        
        return sorted_articles