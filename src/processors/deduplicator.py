from typing import List, Set
from difflib import SequenceMatcher

from ..models.article import Article
from ..utils.logger import setup_logger


class Deduplicator:
    """記事の重複除去クラス"""
    
    def __init__(self):
        self.logger = setup_logger("deduplicator")
        self.seen_hashes: Set[str] = set()
        self.seen_urls: Set[str] = set()
        self.seen_titles: List[str] = []
    
    def remove_duplicates(self, articles: List[Article]) -> List[Article]:
        """重複記事を除去"""
        unique_articles = []
        duplicates_count = 0
        
        for article in articles:
            if self._is_duplicate(article):
                duplicates_count += 1
                continue
            
            # 重複でない場合は追加
            unique_articles.append(article)
            self._mark_as_seen(article)
        
        self.logger.info(f"Removed {duplicates_count} duplicate articles out of {len(articles)}")
        self.logger.info(f"Unique articles: {len(unique_articles)}")
        
        return unique_articles
    
    def _is_duplicate(self, article: Article) -> bool:
        """記事が重複かどうかチェック"""
        
        # 1. コンテンツハッシュによる完全一致チェック
        if article.content_hash in self.seen_hashes:
            self.logger.debug(f"Duplicate by hash: {article.title}")
            return True
        
        # 2. URLによる重複チェック
        normalized_url = self._normalize_url(article.url)
        if normalized_url in self.seen_urls:
            self.logger.debug(f"Duplicate by URL: {article.title}")
            return True
        
        # 3. タイトルの類似度による重複チェック
        if self._is_similar_title(article.title):
            self.logger.debug(f"Duplicate by similar title: {article.title}")
            return True
        
        return False
    
    def _mark_as_seen(self, article: Article):
        """記事を既知として記録"""
        self.seen_hashes.add(article.content_hash)
        self.seen_urls.add(self._normalize_url(article.url))
        self.seen_titles.append(article.title.lower())
    
    def _normalize_url(self, url: str) -> str:
        """URLを正規化"""
        # URLパラメータやフラグメントを除去
        url = url.split('?')[0].split('#')[0]
        
        # 末尾のスラッシュを除去
        url = url.rstrip('/')
        
        # プロトコルを統一
        if url.startswith('http://'):
            url = url.replace('http://', 'https://')
        
        return url.lower()
    
    def _is_similar_title(self, title: str, threshold: float = 0.85) -> bool:
        """タイトルが既存のものと類似しているかチェック"""
        title_lower = title.lower()
        
        for seen_title in self.seen_titles:
            similarity = SequenceMatcher(None, title_lower, seen_title).ratio()
            if similarity >= threshold:
                return True
        
        return False