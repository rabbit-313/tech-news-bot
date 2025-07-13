from abc import ABC, abstractmethod
from typing import List
from datetime import datetime, timedelta
import re

from ..models.article import Article
from ..utils.logger import setup_logger


class BaseCollector(ABC):
    """データ収集の基底クラス"""
    
    def __init__(self, source_name: str):
        self.source_name = source_name
        self.logger = setup_logger(f"collector.{source_name}")
    
    @abstractmethod
    def collect(self) -> List[Article]:
        """記事を収集する（各サブクラスで実装）"""
        pass
    
    def _calculate_score(self, title: str, summary: str = "", **kwargs) -> float:
        """記事の重要度スコアを計算"""
        score = 0.0
        
        # タイトルベースのスコアリング
        title_lower = title.lower()
        
        # 技術キーワードのマッチング
        tech_keywords = [
            "ai", "machine learning", "python", "javascript", "react", "nodejs",
            "docker", "kubernetes", "aws", "cloud", "api", "microservices",
            "blockchain", "rust", "go", "typescript", "devops", "security"
        ]
        
        for keyword in tech_keywords:
            if keyword in title_lower:
                score += 0.1
        
        # 人気指標（ある場合）
        if 'upvotes' in kwargs and kwargs['upvotes']:
            score += min(kwargs['upvotes'] / 1000, 0.3)
        
        if 'stars' in kwargs and kwargs['stars']:
            score += min(kwargs['stars'] / 10000, 0.3)
        
        if 'comments' in kwargs and kwargs['comments']:
            score += min(kwargs['comments'] / 100, 0.2)
        
        # 長さベースの調整
        if len(title) > 10:
            score += 0.1
        
        if summary and len(summary) > 50:
            score += 0.1
        
        # 除外キーワードチェック
        exclude_keywords = ["advertisement", "sponsored", "crypto scam"]
        for keyword in exclude_keywords:
            if keyword in title_lower:
                score -= 0.5
        
        return min(max(score, 0.0), 1.0)
    
    def _extract_tags(self, title: str, content: str = "") -> List[str]:
        """タイトルと内容からタグを抽出"""
        tags = []
        text = f"{title} {content}".lower()
        
        # 技術タグの辞書
        tag_patterns = {
            "python": r"\bpython\b",
            "javascript": r"\b(javascript|js)\b",
            "react": r"\breact\b",
            "nodejs": r"\b(nodejs|node\.js)\b",
            "docker": r"\bdocker\b",
            "kubernetes": r"\b(kubernetes|k8s)\b",
            "aws": r"\baws\b",
            "ai": r"\b(ai|artificial intelligence)\b",
            "ml": r"\b(machine learning|ml)\b",
            "api": r"\bapi\b",
            "security": r"\bsecurity\b",
            "devops": r"\bdevops\b",
            "cloud": r"\bcloud\b",
            "rust": r"\brust\b",
            "go": r"\b(golang|go)\b",
            "typescript": r"\btypescript\b"
        }
        
        for tag, pattern in tag_patterns.items():
            if re.search(pattern, text):
                tags.append(tag)
        
        return tags
    
    def _is_recent(self, published_at: datetime, hours_back: int = 12) -> bool:
        """指定された時間内の記事かチェック"""
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        return published_at >= cutoff_time
    
    def _clean_text(self, text: str) -> str:
        """テキストをクリーンアップ"""
        if not text:
            return ""
        
        # HTMLタグを除去
        text = re.sub(r'<[^>]+>', '', text)
        
        # 余分な空白を除去
        text = re.sub(r'\s+', ' ', text).strip()
        
        # 文字数制限
        if len(text) > 500:
            text = text[:497] + "..."
        
        return text