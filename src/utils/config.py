import os
from typing import Optional


class Config:
    """設定管理クラス"""
    
    # Slack設定
    SLACK_WEBHOOK_URL: Optional[str] = os.getenv('SLACK_WEBHOOK_URL')
    SLACK_BOT_TOKEN: Optional[str] = os.getenv('SLACK_BOT_TOKEN')
    SLACK_CHANNEL: str = os.getenv('SLACK_CHANNEL', '#general')
    
    # GitHub設定
    GITHUB_TOKEN: Optional[str] = os.getenv('GITHUB_TOKEN')
    
    # Reddit設定
    REDDIT_CLIENT_ID: Optional[str] = os.getenv('REDDIT_CLIENT_ID')
    REDDIT_CLIENT_SECRET: Optional[str] = os.getenv('REDDIT_CLIENT_SECRET')
    REDDIT_USER_AGENT: str = "tech-news-bot/1.0"
    
    # RSS フィード設定
    RSS_FEEDS = [
        {"url": "https://hnrss.org/frontpage", "source": "hackernews"},
        {"url": "https://feeds.feedburner.com/venturebeat/SZYF", "source": "venturebeat"},
        {"url": "https://zenn.dev/feed", "source": "zenn"},
        {"url": "https://qiita.com/popular-items/feed", "source": "qiita"},
    ]
    
    # GitHub設定
    GITHUB_TRENDING_LANGUAGES = ["python", "javascript", "typescript", "go", "rust"]
    
    # Reddit設定  
    REDDIT_SUBREDDITS = ["programming", "webdev", "MachineLearning", "devops"]
    
    # フィルタリング設定
    MIN_SCORE_THRESHOLD = 0.3
    MAX_ARTICLES_PER_NOTIFICATION = 10
    HOURS_LOOKBACK = 12  # 何時間前までの記事を収集するか
    
    # キーワードフィルタ
    TECH_KEYWORDS = [
        "ai", "machine learning", "python", "javascript", "react", "node.js",
        "docker", "kubernetes", "aws", "cloud", "api", "microservices",
        "blockchain", "cryptocurrency", "web3", "rust", "go", "typescript",
        "frontend", "backend", "devops", "cicd", "database", "security"
    ]
    
    EXCLUDE_KEYWORDS = [
        "crypto scam", "investment", "trading signals", "buy now", "advertisement"
    ]
    
    @classmethod
    def validate(cls) -> bool:
        """必要な設定が揃っているかチェック"""
        required_vars = [
            "SLACK_WEBHOOK_URL"
        ]
        
        missing_vars = []
        for var in required_vars:
            if not getattr(cls, var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"Missing required environment variables: {', '.join(missing_vars)}")
            return False
        
        return True