import re
from typing import List

from ..models.article import Article
from ..utils.config import Config
from ..utils.logger import setup_logger


class ContentFilter:
    """コンテンツフィルタリングクラス"""
    
    def __init__(self):
        self.logger = setup_logger("content_filter")
    
    def filter(self, articles: List[Article]) -> List[Article]:
        """記事をフィルタリング"""
        filtered_articles = []
        filtered_count = 0
        
        for article in articles:
            if self._should_include(article):
                filtered_articles.append(article)
            else:
                filtered_count += 1
        
        self.logger.info(f"Filtered out {filtered_count} articles")
        self.logger.info(f"Remaining articles: {len(filtered_articles)}")
        
        return filtered_articles
    
    def _should_include(self, article: Article) -> bool:
        """記事を含めるべきかどうか判定"""
        
        # 1. スコアによるフィルタリング
        if article.score < Config.MIN_SCORE_THRESHOLD:
            self.logger.debug(f"Filtered by low score: {article.title} (score: {article.score})")
            return False
        
        # 2. 除外キーワードチェック
        if self._contains_exclude_keywords(article):
            self.logger.debug(f"Filtered by exclude keywords: {article.title}")
            return False
        
        # 3. スパムコンテンツチェック
        if self._is_spam_content(article):
            self.logger.debug(f"Filtered as spam: {article.title}")
            return False
        
        # 4. 技術関連コンテンツチェック
        if not self._is_tech_related(article):
            self.logger.debug(f"Filtered as non-tech: {article.title}")
            return False
        
        # 5. 最小品質チェック
        if not self._meets_quality_standards(article):
            self.logger.debug(f"Filtered by quality: {article.title}")
            return False
        
        return True
    
    def _contains_exclude_keywords(self, article: Article) -> bool:
        """除外キーワードが含まれているかチェック"""
        text = f"{article.title} {article.summary}".lower()
        
        for keyword in Config.EXCLUDE_KEYWORDS:
            if keyword.lower() in text:
                return True
        
        return False
    
    def _is_spam_content(self, article: Article) -> bool:
        """スパムコンテンツかどうかチェック"""
        title = article.title.lower()
        summary = article.summary.lower()
        
        # スパムの特徴パターン
        spam_patterns = [
            r'\b(buy now|click here|limited time|act fast)\b',
            r'\b(make money|get rich|earn \$\d+)\b',
            r'\b(free trial|no credit card|risk free)\b',
            r'[!]{3,}',  # 過度の感嘆符
            r'[A-Z]{10,}',  # 過度の大文字
            r'\b(crypto|bitcoin|ethereum).*(profit|investment|trading)\b'
        ]
        
        text = f"{title} {summary}"
        for pattern in spam_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def _is_tech_related(self, article: Article) -> bool:
        """技術関連の記事かどうかチェック"""
        text = f"{article.title} {article.summary} {' '.join(article.tags)}".lower()
        
        # 技術キーワードがあれば通す
        for keyword in Config.TECH_KEYWORDS:
            if keyword.lower() in text:
                return True
        
        # ソース別の判定
        tech_sources = ["github", "hackernews", "zenn", "qiita"]
        if article.source in tech_sources:
            return True
        
        # Reddit の場合は技術系サブレディットか確認
        if article.source == "reddit":
            tech_subreddits = ["r/programming", "r/webdev", "r/machinelearning", "r/devops"]
            for tag in article.tags:
                if any(sub in tag for sub in tech_subreddits):
                    return True
        
        return False
    
    def _meets_quality_standards(self, article: Article) -> bool:
        """最小品質基準を満たしているかチェック"""
        
        # タイトルの長さチェック
        if len(article.title.strip()) < 10:
            return False
        
        # URLの有効性チェック
        if not article.url or not article.url.startswith(('http://', 'https://')):
            return False
        
        # タイトルが意味のある内容かチェック
        title_lower = article.title.lower()
        meaningless_patterns = [
            r'^(test|testing|hello|hi)$',
            r'^[a-z]{1,3}$',  # 短すぎる
            r'^\d+$',  # 数字のみ
        ]
        
        for pattern in meaningless_patterns:
            if re.match(pattern, title_lower):
                return False
        
        return True