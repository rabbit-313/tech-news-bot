import praw
from datetime import datetime
from typing import List, Optional
import time

from .base_collector import BaseCollector
from ..models.article import Article
from ..utils.config import Config


class RedditCollector(BaseCollector):
    """Reddit 人気投稿収集クラス"""
    
    def __init__(self):
        super().__init__("reddit")
        self.client_id = Config.REDDIT_CLIENT_ID
        self.client_secret = Config.REDDIT_CLIENT_SECRET
        self.user_agent = Config.REDDIT_USER_AGENT
        
        # Reddit API クライアント初期化
        self.reddit = None
        if self.client_id and self.client_secret:
            try:
                self.reddit = praw.Reddit(
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                    user_agent=self.user_agent
                )
                # Read-only mode設定
                self.reddit.read_only = True
            except Exception as e:
                self.logger.error(f"Failed to initialize Reddit client: {e}")
    
    def collect(self) -> List[Article]:
        """Redditから人気投稿を収集"""
        if not self.reddit:
            self.logger.warning("Reddit client not initialized, skipping Reddit collection")
            return []
        
        all_articles = []
        
        for subreddit_name in Config.REDDIT_SUBREDDITS:
            try:
                self.logger.info(f"Fetching posts from r/{subreddit_name}")
                articles = self._collect_from_subreddit(subreddit_name)
                all_articles.extend(articles)
                self.logger.info(f"Collected {len(articles)} posts from r/{subreddit_name}")
                
                # API制限対策
                time.sleep(2)
                
            except Exception as e:
                self.logger.error(f"Failed to fetch from r/{subreddit_name}: {e}")
        
        return all_articles
    
    def _collect_from_subreddit(self, subreddit_name: str) -> List[Article]:
        """特定のサブレディットから投稿を収集"""
        articles = []
        
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            
            # 今日のホット投稿を取得（上位20個）
            for submission in subreddit.hot(limit=20):
                try:
                    article = self._create_article_from_submission(submission, subreddit_name)
                    if article:
                        articles.append(article)
                except Exception as e:
                    self.logger.error(f"Failed to process submission {submission.id}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Failed to access subreddit r/{subreddit_name}: {e}")
        
        return articles
    
    def _create_article_from_submission(self, submission, subreddit_name: str) -> Optional[Article]:
        """Reddit投稿から記事を作成"""
        try:
            # 基本情報
            title = submission.title
            url = submission.url
            
            # テキスト投稿の場合はRedditのURLを使用
            if submission.is_self:
                url = f"https://reddit.com{submission.permalink}"
            
            # 投稿時刻
            published_at = datetime.fromtimestamp(submission.created_utc)
            
            # 古い投稿は除外
            if not self._is_recent(published_at, Config.HOURS_LOOKBACK):
                return None
            
            # 概要を作成
            summary = self._create_summary(submission)
            
            # スコア計算
            score = self._calculate_score(
                title=title,
                summary=summary,
                upvotes=submission.score,
                comments=submission.num_comments
            )
            
            # 最小スコア未満は除外
            if score < Config.MIN_SCORE_THRESHOLD:
                return None
            
            # タグ抽出
            tags = self._extract_tags(title, summary)
            tags.append(f"r/{subreddit_name}")
            
            article = Article(
                title=self._clean_text(title),
                url=url,
                summary=self._clean_text(summary),
                published_at=published_at,
                source="reddit",
                tags=tags,
                score=score,
                content_hash="",  # __post_init__で生成される
                author=submission.author.name if submission.author else None
            )
            
            return article
            
        except Exception as e:
            self.logger.error(f"Failed to create article from Reddit submission: {e}")
            return None
    
    def _create_summary(self, submission) -> str:
        """投稿から概要を作成"""
        summary_parts = []
        
        # セルフポストの場合は本文を使用
        if submission.is_self and submission.selftext:
            # 本文の最初の200文字
            text = submission.selftext.strip()
            if text:
                summary_parts.append(text[:200])
        
        # 統計情報を追加
        stats = f"👍 {submission.score} upvotes, 💬 {submission.num_comments} comments"
        summary_parts.append(stats)
        
        # フレアがある場合は追加
        if submission.link_flair_text:
            summary_parts.append(f"[{submission.link_flair_text}]")
        
        return " | ".join(summary_parts) if summary_parts else f"Reddit post with {submission.score} upvotes"