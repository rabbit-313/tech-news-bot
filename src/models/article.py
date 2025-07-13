from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
import hashlib


@dataclass
class Article:
    """記事データモデル"""
    title: str                    # 記事タイトル
    url: str                      # 記事URL
    summary: str                  # 要約（AI生成 or 抜粋）
    published_at: datetime        # 公開日時
    source: str                   # データソース（rss, github, reddit）
    tags: List[str]               # タグ・カテゴリ
    score: float                  # 重要度スコア（0.0-1.0）
    content_hash: str             # 重複検出用ハッシュ
    author: Optional[str] = None  # 著者名
    
    def to_slack_message(self) -> dict:
        """Slack通知用メッセージ形式に変換"""
        emoji_map = {
            "github": "🔧",
            "reddit": "💬", 
            "hackernews": "📰",
            "techcrunch": "🚀",
            "zenn": "📝",
            "qiita": "💡"
        }
        
        emoji = emoji_map.get(self.source, "📰")
        score_emoji = "⭐" * min(int(self.score * 5), 5)
        
        return {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{emoji} *{self.title}*\n{self.summary}\n\n{score_emoji} Score: {self.score:.2f} | Source: {self.source.title()}"
                    },
                    "accessory": {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Read More"},
                        "url": self.url
                    }
                }
            ]
        }
    
    @classmethod
    def generate_content_hash(cls, title: str, url: str) -> str:
        """タイトルとURLから重複検出用ハッシュを生成"""
        content = f"{title.lower()}{url.lower()}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def __post_init__(self):
        """初期化後の処理"""
        if not self.content_hash:
            self.content_hash = self.generate_content_hash(self.title, self.url)