import requests
import json
from datetime import datetime
from typing import List

from ..models.article import Article
from ..utils.config import Config
from ..utils.logger import setup_logger


class SlackNotifier:
    """Slack通知クラス"""
    
    def __init__(self):
        self.logger = setup_logger("slack_notifier")
        self.webhook_url = Config.SLACK_WEBHOOK_URL
    
    def send_daily_summary(self, articles: List[Article]) -> bool:
        """日次サマリーをSlackに送信"""
        if not self.webhook_url:
            self.logger.error("Slack webhook URL not configured")
            return False
        
        if not articles:
            self.logger.info("No articles to send")
            return True
        
        try:
            # 記事数を制限
            top_articles = articles[:Config.MAX_ARTICLES_PER_NOTIFICATION]
            
            # メッセージ作成
            message = self._create_summary_message(top_articles)
            
            # Slack送信
            response = requests.post(
                self.webhook_url,
                headers={'Content-Type': 'application/json'},
                data=json.dumps(message),
                timeout=30
            )
            
            if response.status_code == 200:
                self.logger.info(f"Successfully sent {len(top_articles)} articles to Slack")
                return True
            else:
                self.logger.error(f"Failed to send to Slack: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending to Slack: {e}")
            return False
    
    def _create_summary_message(self, articles: List[Article]) -> dict:
        """サマリーメッセージを作成"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # ヘッダーブロック
        header_text = f"🚀 *Tech News Daily Summary* - {current_time}\n\n"
        header_text += f"Found {len(articles)} top tech articles for you:"
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🚀 Tech News Daily Summary"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{current_time}* | {len(articles)} top articles"
                }
            },
            {
                "type": "divider"
            }
        ]
        
        # 各記事のブロック
        for i, article in enumerate(articles, 1):
            article_block = self._create_article_block(article, i)
            blocks.append(article_block)
            
            # 記事間の区切り（最後の記事以外）
            if i < len(articles):
                blocks.append({"type": "divider"})
        
        # フッターブロック
        footer_block = {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"📊 Powered by Tech News Bot | Sources: RSS, GitHub, Reddit"
                }
            ]
        }
        blocks.append(footer_block)
        
        return {"blocks": blocks}
    
    def _create_article_block(self, article: Article, index: int) -> dict:
        """個別記事のブロックを作成"""
        # ソース別絵文字
        emoji_map = {
            "github": "🔧",
            "reddit": "💬", 
            "hackernews": "📰",
            "techcrunch": "🚀",
            "venturebeat": "💼",
            "zenn": "📝",
            "qiita": "💡"
        }
        
        emoji = emoji_map.get(article.source, "📰")
        score_stars = "⭐" * min(int(article.score * 5), 5)
        
        # タグ表示（最大3個）
        tags_text = ""
        if article.tags:
            display_tags = article.tags[:3]
            tags_text = " | " + " • ".join([f"`{tag}`" for tag in display_tags])
        
        # 著者情報
        author_text = ""
        if article.author:
            author_text = f" by {article.author}"
        
        # メイン記事ブロック
        article_text = f"{emoji} *{index}. {article.title}*{author_text}\n"
        article_text += f"{article.summary}\n\n"
        article_text += f"{score_stars} *Score: {article.score:.2f}* | Source: {article.source.title()}{tags_text}"
        
        return {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": article_text
            },
            "accessory": {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Read More"
                },
                "url": article.url,
                "action_id": f"read_more_{index}"
            }
        }
    
    def send_error_notification(self, error_message: str) -> bool:
        """エラー通知を送信"""
        if not self.webhook_url:
            return False
        
        try:
            message = {
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "⚠️ Tech News Bot Error"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"An error occurred during news collection:\n\n```{error_message}```"
                        }
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                            }
                        ]
                    }
                ]
            }
            
            response = requests.post(
                self.webhook_url,
                headers={'Content-Type': 'application/json'},
                data=json.dumps(message),
                timeout=30
            )
            
            return response.status_code == 200
            
        except Exception:
            return False