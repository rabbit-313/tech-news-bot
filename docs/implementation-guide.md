# Tech News Bot - 実装ガイド

## 実装フェーズ計画

### Phase 1: MVP (Minimum Viable Product) - 2-3週間

**目標**: 基本的な記事収集とSlack通知機能

**実装内容**:
- RSS収集機能
- 基本的なフィルタリング
- Slack通知機能
- DynamoDB保存
- 手動実行テスト

### Phase 2: 機能拡張 - 2-3週間

**目標**: データソースの拡充と処理品質向上

**実装内容**:
- GitHub API連携
- Reddit API連携
- 重複除去の高度化
- スコアリング機能
- スケジュール実行

### Phase 3: AI統合 - 2-3週間

**目標**: AI による要約と品質向上

**実装内容**:
- OpenAI API統合
- 記事要約機能
- 感情分析・重要度判定
- パーソナライゼーション基盤

### Phase 4: 運用最適化 - 継続的

**目標**: パフォーマンスと運用性の向上

**実装内容**:
- パフォーマンス改善
- コスト最適化
- 監視・アラート強化
- ユーザーフィードバック対応

## Phase 1: MVP実装

### Step 1: プロジェクト初期セットアップ

#### 1.1 ディレクトリ構造作成

```bash
mkdir -p tech-news-bot/{src/{collectors,processors,notifiers,models,utils},lambda_functions,tests/{unit,integration},docs,infrastructure}

# ファイル作成
touch tech-news-bot/src/{__init__.py,collectors/__init__.py,processors/__init__.py,notifiers/__init__.py,models/__init__.py,utils/__init__.py}
touch tech-news-bot/lambda_functions/{collector_handler.py,notifier_handler.py}
touch tech-news-bot/{requirements.txt,requirements-dev.txt,serverless.yml}
```

#### 1.2 requirements.txt 作成

```txt
# requirements.txt
boto3==1.34.0
requests==2.31.0
feedparser==6.0.10
structlog==23.2.0
pydantic==2.5.0
python-dateutil==2.8.2
```

```txt
# requirements-dev.txt
pytest==7.4.3
pytest-mock==3.12.0
black==23.11.0
flake8==6.1.0
mypy==1.7.1
moto==4.2.14
```

#### 1.3 基本設定ファイル

```yaml
# serverless.yml
service: tech-news-bot

frameworkVersion: '3'

provider:
  name: aws
  runtime: python3.11
  region: ap-northeast-1
  memorySize: 512
  timeout: 300
  
  environment:
    DYNAMODB_TABLE: ${self:service}-articles-${sls:stage}
    STAGE: ${sls:stage}
    
  iam:
    role:
      statements:
        - Effect: Allow
          Action:
            - dynamodb:PutItem
            - dynamodb:GetItem
            - dynamodb:Query
            - dynamodb:UpdateItem
          Resource: !GetAtt ArticlesTable.Arn
        - Effect: Allow
          Action:
            - ssm:GetParameter
          Resource: !Sub 'arn:aws:ssm:${AWS::Region}:${AWS::AccountId}:parameter/tech-news-bot/*'

functions:
  collector:
    handler: lambda_functions.collector_handler.handler
    timeout: 300
    memorySize: 1024
    
  notifier:
    handler: lambda_functions.notifier_handler.handler
    timeout: 60
    memorySize: 256

resources:
  Resources:
    ArticlesTable:
      Type: AWS::DynamoDB::Table
      Properties:
        TableName: ${self:service}-articles-${sls:stage}
        BillingMode: PAY_PER_REQUEST
        AttributeDefinitions:
          - AttributeName: date
            AttributeType: S
          - AttributeName: article_id
            AttributeType: S
        KeySchema:
          - AttributeName: date
            KeyType: HASH
          - AttributeName: article_id
            KeyType: RANGE
        TimeToLiveSpecification:
          AttributeName: ttl
          Enabled: true

plugins:
  - serverless-python-requirements

custom:
  pythonRequirements:
    dockerizePip: non-linux
    slim: true
    strip: false
```

### Step 2: データモデル実装

#### 2.1 Article モデル

```python
# src/models/article.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
import hashlib
import uuid

@dataclass
class Article:
    """記事データモデル"""
    title: str
    url: str
    summary: str
    published_at: datetime
    source: str
    tags: List[str] = field(default_factory=list)
    score: float = 0.5
    content_hash: str = ""
    author: Optional[str] = None
    article_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def __post_init__(self):
        """初期化後の処理"""
        if not self.content_hash:
            self.content_hash = self._generate_content_hash()
    
    def _generate_content_hash(self) -> str:
        """コンテンツハッシュを生成"""
        content = f"{self.title}{self.url}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def to_dynamodb_item(self) -> dict:
        """DynamoDB アイテム形式に変換"""
        from decimal import Decimal
        
        date_str = self.published_at.strftime('%Y-%m-%d')
        ttl = int((datetime.now().timestamp()) + (30 * 24 * 60 * 60))  # 30日後
        
        return {
            'date': date_str,
            'article_id': self.article_id,
            'title': self.title,
            'url': self.url,
            'summary': self.summary,
            'published_at': int(self.published_at.timestamp()),
            'source': self.source,
            'tags': self.tags,
            'score': Decimal(str(self.score)),
            'content_hash': self.content_hash,
            'author': self.author,
            'ttl': ttl
        }
    
    @classmethod
    def from_dynamodb_item(cls, item: dict) -> 'Article':
        """DynamoDB アイテムから Article インスタンスを作成"""
        return cls(
            title=item['title'],
            url=item['url'],
            summary=item['summary'],
            published_at=datetime.fromtimestamp(item['published_at']),
            source=item['source'],
            tags=item.get('tags', []),
            score=float(item.get('score', 0.5)),
            content_hash=item['content_hash'],
            author=item.get('author'),
            article_id=item['article_id']
        )
    
    def to_slack_block(self, index: int) -> dict:
        """Slack ブロック形式に変換"""
        # スコアに応じた絵文字
        if self.score >= 0.9:
            score_emoji = "🔥"
        elif self.score >= 0.8:
            score_emoji = "⭐"
        elif self.score >= 0.7:
            score_emoji = "👍"
        else:
            score_emoji = "📄"
        
        return {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{score_emoji} *{index}. {self.title}*\n{self.summary}"
            },
            "accessory": {
                "type": "button",
                "text": {"type": "plain_text", "text": "Read More"},
                "url": self.url
            }
        }
```

### Step 3: 設定管理

#### 3.1 設定クラス

```python
# src/utils/config.py
import os
import boto3
from typing import Optional
import structlog

logger = structlog.get_logger()

class Config:
    """設定管理クラス"""
    
    def __init__(self):
        self.stage = os.getenv('STAGE', 'dev')
        self.region = os.getenv('AWS_DEFAULT_REGION', 'ap-northeast-1')
        self.dynamodb_table = os.getenv('DYNAMODB_TABLE')
        
        # SSM Client
        self.ssm = boto3.client('ssm', region_name=self.region)
        
        # キャッシュ
        self._cache = {}
    
    def get_parameter(self, name: str, decrypt: bool = True) -> Optional[str]:
        """SSM Parameter Store から値を取得"""
        cache_key = f"{name}_{decrypt}"
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            full_name = f"/tech-news-bot/{name}"
            response = self.ssm.get_parameter(
                Name=full_name,
                WithDecryption=decrypt
            )
            
            value = response['Parameter']['Value']
            self._cache[cache_key] = value
            return value
            
        except self.ssm.exceptions.ParameterNotFound:
            logger.warning(f"Parameter not found: {full_name}")
            return None
        except Exception as e:
            logger.error(f"Failed to get parameter {name}: {e}")
            return None
    
    @property
    def slack_webhook_url(self) -> Optional[str]:
        return self.get_parameter('slack-webhook-url')
    
    @property
    def github_token(self) -> Optional[str]:
        return self.get_parameter('github-token')
    
    @property
    def reddit_client_id(self) -> Optional[str]:
        return self.get_parameter('reddit-client-id')
    
    @property
    def reddit_client_secret(self) -> Optional[str]:
        return self.get_parameter('reddit-client-secret')
    
    @property
    def openai_api_key(self) -> Optional[str]:
        return self.get_parameter('openai-api-key')

# グローバル設定インスタンス
config = Config()
```

#### 3.2 ログ設定

```python
# src/utils/logger.py
import structlog
import logging
import os

def setup_logging():
    """構造化ログ設定"""
    
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    is_local = os.getenv('AWS_EXECUTION_ENV') is None
    
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.dev.ConsoleRenderer() if is_local else structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # 標準ログレベル設定
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(message)s"
    )

# 初期化
setup_logging()
```

### Step 4: RSS収集機能実装

#### 4.1 Base Collector

```python
# src/collectors/base_collector.py
from abc import ABC, abstractmethod
from typing import List
import structlog
from src.models.article import Article

class BaseCollector(ABC):
    """データ収集の基底クラス"""
    
    def __init__(self):
        self.logger = structlog.get_logger(self.__class__.__name__)
    
    @abstractmethod
    def collect(self) -> List[Article]:
        """記事を収集（サブクラスで実装）"""
        pass
    
    @property
    @abstractmethod
    def source_name(self) -> str:
        """データソース名"""
        pass
```

#### 4.2 RSS Collector

```python
# src/collectors/rss_collector.py
import feedparser
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any
from src.collectors.base_collector import BaseCollector
from src.models.article import Article

class RSSCollector(BaseCollector):
    """RSS/Atom フィード収集"""
    
    RSS_FEEDS = [
        {
            "url": "https://hnrss.org/frontpage",
            "source": "hackernews",
            "weight": 0.9,
            "language": "en"
        },
        {
            "url": "https://japan.techcrunch.com/feed/",
            "source": "techcrunch",
            "weight": 0.8,
            "language": "ja"
        },
        {
            "url": "https://zenn.dev/feed",
            "source": "zenn",
            "weight": 0.7,
            "language": "ja"
        },
        {
            "url": "https://qiita.com/popular-items/feed",
            "source": "qiita",
            "weight": 0.6,
            "language": "ja"
        }
    ]
    
    @property
    def source_name(self) -> str:
        return "rss"
    
    def collect(self) -> List[Article]:
        """RSS フィードから記事を収集"""
        all_articles = []
        cutoff_time = datetime.now() - timedelta(hours=12)
        
        for feed_config in self.RSS_FEEDS:
            try:
                articles = self._collect_from_feed(feed_config, cutoff_time)
                all_articles.extend(articles)
                
                self.logger.info(
                    "rss_feed_collected",
                    feed_url=feed_config["url"],
                    source=feed_config["source"],
                    articles_count=len(articles)
                )
                
            except Exception as e:
                self.logger.error(
                    "rss_feed_failed",
                    feed_url=feed_config["url"],
                    error=str(e)
                )
        
        return all_articles
    
    def _collect_from_feed(self, feed_config: Dict[str, Any], cutoff_time: datetime) -> List[Article]:
        """個別フィードから記事を収集"""
        
        # RSS フィード取得
        response = requests.get(feed_config["url"], timeout=30)
        response.raise_for_status()
        
        feed = feedparser.parse(response.content)
        articles = []
        
        for entry in feed.entries:
            try:
                published_time = self._parse_published_time(entry)
                
                # 12時間以内の記事のみ
                if published_time < cutoff_time:
                    continue
                
                article = Article(
                    title=self._clean_title(entry.title),
                    url=entry.link,
                    summary=self._extract_summary(entry),
                    published_at=published_time,
                    source=feed_config["source"],
                    tags=self._extract_tags(entry, feed_config),
                    score=self._calculate_score(entry, feed_config),
                    author=self._extract_author(entry)
                )
                
                articles.append(article)
                
            except Exception as e:
                self.logger.warning(
                    "rss_entry_failed",
                    entry_title=getattr(entry, 'title', 'Unknown'),
                    error=str(e)
                )
        
        return articles
    
    def _parse_published_time(self, entry) -> datetime:
        """公開時刻をパース"""
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            import time
            return datetime.fromtimestamp(time.mktime(entry.published_parsed))
        elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            import time
            return datetime.fromtimestamp(time.mktime(entry.updated_parsed))
        else:
            return datetime.now()
    
    def _clean_title(self, title: str) -> str:
        """タイトルのクリーニング"""
        # HTMLタグの除去
        import re
        title = re.sub(r'<[^>]+>', '', title)
        
        # 余分な空白の除去
        title = ' '.join(title.split())
        
        return title.strip()
    
    def _extract_summary(self, entry) -> str:
        """要約の抽出"""
        if hasattr(entry, 'summary') and entry.summary:
            summary = entry.summary
        elif hasattr(entry, 'description') and entry.description:
            summary = entry.description
        else:
            return "No summary available"
        
        # HTMLタグの除去
        import re
        summary = re.sub(r'<[^>]+>', '', summary)
        
        # 改行・余分な空白の正規化
        summary = ' '.join(summary.split())
        
        # 長すぎる場合は切り詰め
        if len(summary) > 300:
            summary = summary[:297] + "..."
        
        return summary.strip()
    
    def _extract_tags(self, entry, feed_config: Dict[str, Any]) -> List[str]:
        """タグの抽出"""
        tags = [feed_config["source"]]
        
        # フィード固有のタグ
        if hasattr(entry, 'tags') and entry.tags:
            for tag in entry.tags[:3]:  # 最大3個
                if hasattr(tag, 'term'):
                    tags.append(tag.term.lower())
        
        # 言語タグ
        tags.append(feed_config["language"])
        
        return list(set(tags))  # 重複除去
    
    def _extract_author(self, entry) -> str:
        """著者の抽出"""
        if hasattr(entry, 'author') and entry.author:
            return entry.author
        elif hasattr(entry, 'dc_creator') and entry.dc_creator:
            return entry.dc_creator
        return None
    
    def _calculate_score(self, entry, feed_config: Dict[str, Any]) -> float:
        """記事スコアの計算"""
        base_score = feed_config["weight"]
        
        # タイトル長によるボーナス（適度な長さ）
        title_len = len(entry.title)
        if 20 <= title_len <= 100:
            base_score += 0.1
        
        # キーワードボーナス
        tech_keywords = ['ai', 'ml', 'python', 'javascript', 'react', 'api', 'aws', 'kubernetes']
        content = f"{entry.title} {getattr(entry, 'summary', '')}".lower()
        keyword_matches = sum(1 for keyword in tech_keywords if keyword in content)
        base_score += min(keyword_matches * 0.05, 0.2)
        
        return min(base_score, 1.0)
```

### Step 5: データ保存機能

#### 5.1 Article Store

```python
# src/utils/article_store.py
import boto3
from boto3.dynamodb.conditions import Key, Attr
from typing import List, Set
from datetime import datetime, date, timedelta
import structlog
from src.models.article import Article
from src.utils.config import config

class ArticleStore:
    """DynamoDB を使用した記事ストレージ"""
    
    def __init__(self):
        self.logger = structlog.get_logger(self.__class__.__name__)
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(config.dynamodb_table)
    
    def save_articles(self, articles: List[Article]) -> int:
        """記事を一括保存"""
        saved_count = 0
        
        try:
            with self.table.batch_writer() as batch:
                for article in articles:
                    try:
                        item = article.to_dynamodb_item()
                        batch.put_item(Item=item)
                        saved_count += 1
                        
                    except Exception as e:
                        self.logger.error(
                            "article_save_failed",
                            article_title=article.title,
                            error=str(e)
                        )
            
            self.logger.info(
                "articles_saved",
                total_articles=len(articles),
                saved_count=saved_count
            )
            
            return saved_count
            
        except Exception as e:
            self.logger.error(
                "batch_save_failed",
                error=str(e)
            )
            return 0
    
    def get_articles_by_date(self, target_date: date, min_score: float = 0.0) -> List[Article]:
        """日付指定で記事を取得"""
        date_str = target_date.strftime('%Y-%m-%d')
        
        try:
            response = self.table.query(
                KeyConditionExpression=Key('date').eq(date_str),
                FilterExpression=Attr('score').gte(min_score),
                ScanIndexForward=False  # 新しい順
            )
            
            articles = []
            for item in response['Items']:
                article = Article.from_dynamodb_item(item)
                articles.append(article)
            
            self.logger.info(
                "articles_retrieved",
                date=date_str,
                count=len(articles),
                min_score=min_score
            )
            
            return articles
            
        except Exception as e:
            self.logger.error(
                "articles_retrieval_failed",
                date=date_str,
                error=str(e)
            )
            return []
    
    def get_existing_hashes(self, days_back: int = 7) -> Set[str]:
        """過去N日間の記事ハッシュを取得（重複検出用）"""
        hashes = set()
        
        for i in range(days_back):
            target_date = date.today() - timedelta(days=i)
            date_str = target_date.strftime('%Y-%m-%d')
            
            try:
                response = self.table.query(
                    KeyConditionExpression=Key('date').eq(date_str),
                    ProjectionExpression='content_hash'
                )
                
                for item in response['Items']:
                    hashes.add(item['content_hash'])
                    
            except Exception as e:
                self.logger.warning(
                    "hash_retrieval_failed",
                    date=date_str,
                    error=str(e)
                )
        
        self.logger.info(
            "existing_hashes_retrieved",
            hash_count=len(hashes),
            days_back=days_back
        )
        
        return hashes
```

### Step 6: Slack通知機能

#### 6.1 Slack Notifier

```python
# src/notifiers/slack_notifier.py
import requests
from typing import List
from datetime import datetime
import structlog
from src.models.article import Article
from src.utils.config import config

class SlackNotifier:
    """Slack 通知機能"""
    
    def __init__(self):
        self.logger = structlog.get_logger(self.__class__.__name__)
        self.webhook_url = config.slack_webhook_url
    
    def send_daily_summary(self, articles: List[Article], title: str = None) -> bool:
        """日次サマリーをSlackに送信"""
        
        if not self.webhook_url:
            self.logger.error("slack_webhook_url_not_configured")
            return False
        
        if not articles:
            self.logger.info("no_articles_to_send")
            return True
        
        # タイトル生成
        if not title:
            current_hour = datetime.now().hour
            if current_hour < 12:
                title = "🌅 今日のテックニュース（朝刊）"
            else:
                title = "🌆 今日のテックニュース（夕刊）"
        
        # Slack メッセージ構築
        blocks = self._build_message_blocks(articles, title)
        
        payload = {
            "blocks": blocks,
            "username": "Tech News Bot",
            "icon_emoji": ":newspaper:"
        }
        
        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                self.logger.info(
                    "slack_notification_sent",
                    articles_count=len(articles),
                    title=title
                )
                return True
            else:
                self.logger.error(
                    "slack_notification_failed",
                    status_code=response.status_code,
                    response_text=response.text
                )
                return False
                
        except Exception as e:
            self.logger.error(
                "slack_notification_error",
                error=str(e)
            )
            return False
    
    def _build_message_blocks(self, articles: List[Article], title: str) -> List[dict]:
        """Slack メッセージブロックを構築"""
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": title
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"📊 {len(articles)}件の記事をお届けします"
                    }
                ]
            },
            {"type": "divider"}
        ]
        
        # 記事ブロック（最大10記事）
        for i, article in enumerate(articles[:10], 1):
            article_blocks = self._create_article_blocks(article, i)
            blocks.extend(article_blocks)
            
            # 5記事ごとに区切り線
            if i % 5 == 0 and i < len(articles):
                blocks.append({"type": "divider"})
        
        # フッター
        blocks.extend([
            {"type": "divider"},
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"🤖 Tech News Bot | {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                    }
                ]
            }
        ])
        
        return blocks
    
    def _create_article_blocks(self, article: Article, index: int) -> List[dict]:
        """個別記事のSlackブロックを作成"""
        
        # スコアに応じた絵文字
        if article.score >= 0.9:
            score_emoji = "🔥"
        elif article.score >= 0.8:
            score_emoji = "⭐"
        elif article.score >= 0.7:
            score_emoji = "👍"
        else:
            score_emoji = "📄"
        
        # ソース絵文字
        source_emojis = {
            'hackernews': '🟠',
            'techcrunch': '🟢',
            'zenn': '🇯🇵',
            'qiita': '🟦'
        }
        source_emoji = source_emojis.get(article.source, '📰')
        
        # タグ表示（最大3個）
        tag_text = ""
        if article.tags:
            displayed_tags = [tag for tag in article.tags if tag not in [article.source, 'en', 'ja']][:3]
            if displayed_tags:
                tag_text = " | " + " ".join([f"`{tag}`" for tag in displayed_tags])
        
        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{score_emoji} *{index}. {article.title}*\n{article.summary}"
                },
                "accessory": {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Read More",
                        "emoji": True
                    },
                    "url": article.url,
                    "action_id": f"read_article_{index}"
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"{source_emoji} {article.source} | Score: {article.score:.2f}{tag_text}"
                    }
                ]
            }
        ]
```

### Step 7: Lambda関数ハンドラー

#### 7.1 Collector Handler

```python
# lambda_functions/collector_handler.py
import json
from datetime import datetime
import structlog
from src.collectors.rss_collector import RSSCollector
from src.utils.article_store import ArticleStore

# ログ設定
from src.utils.logger import setup_logging
setup_logging()

logger = structlog.get_logger()

def handler(event, context):
    """記事収集のメインハンドラー"""
    
    logger.info(
        "collection_started",
        event=event,
        context_request_id=context.aws_request_id
    )
    
    try:
        # RSS収集
        rss_collector = RSSCollector()
        articles = rss_collector.collect()
        
        if not articles:
            logger.info("no_articles_collected")
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "message": "No articles collected",
                    "collected_count": 0
                })
            }
        
        # 重複チェック（簡易版）
        article_store = ArticleStore()
        existing_hashes = article_store.get_existing_hashes()
        
        new_articles = []
        for article in articles:
            if article.content_hash not in existing_hashes:
                new_articles.append(article)
        
        # 保存
        saved_count = article_store.save_articles(new_articles)
        
        logger.info(
            "collection_completed",
            total_collected=len(articles),
            new_articles=len(new_articles),
            saved_count=saved_count
        )
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Collection completed successfully",
                "total_collected": len(articles),
                "new_articles": len(new_articles),
                "saved_count": saved_count
            })
        }
        
    except Exception as e:
        logger.error(
            "collection_failed",
            error=str(e),
            error_type=type(e).__name__
        )
        
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "Collection failed",
                "message": str(e)
            })
        }
```

#### 7.2 Notifier Handler

```python
# lambda_functions/notifier_handler.py
import json
from datetime import datetime, date
import structlog
from src.notifiers.slack_notifier import SlackNotifier
from src.utils.article_store import ArticleStore

# ログ設定
from src.utils.logger import setup_logging
setup_logging()

logger = structlog.get_logger()

def handler(event, context):
    """Slack通知のメインハンドラー"""
    
    logger.info(
        "notification_started",
        event=event,
        context_request_id=context.aws_request_id
    )
    
    try:
        # 本日の記事を取得
        article_store = ArticleStore()
        today_articles = article_store.get_articles_by_date(
            date.today(),
            min_score=0.5  # スコア0.5以上
        )
        
        if not today_articles:
            logger.info("no_articles_to_notify")
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "message": "No articles to notify"
                })
            }
        
        # スコア順でソート
        sorted_articles = sorted(today_articles, key=lambda x: x.score, reverse=True)
        top_articles = sorted_articles[:10]  # 上位10記事
        
        # 時間帯による分類
        current_hour = datetime.now().hour
        if current_hour < 12:
            notification_type = "morning"
            title = "🌅 今日のテックニュース（朝刊）"
        else:
            notification_type = "evening"
            title = "🌆 今日のテックニュース（夕刊）"
        
        # Slack通知
        slack_notifier = SlackNotifier()
        success = slack_notifier.send_daily_summary(top_articles, title)
        
        if success:
            logger.info(
                "notification_completed",
                articles_sent=len(top_articles),
                notification_type=notification_type
            )
            
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "message": "Notification sent successfully",
                    "articles_sent": len(top_articles),
                    "notification_type": notification_type
                })
            }
        else:
            logger.error("notification_failed")
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "error": "Notification failed"
                })
            }
        
    except Exception as e:
        logger.error(
            "notification_error",
            error=str(e),
            error_type=type(e).__name__
        )
        
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "Notification failed",
                "message": str(e)
            })
        }
```

### Step 8: テスト実装

#### 8.1 単体テスト

```python
# tests/unit/test_article.py
import pytest
from datetime import datetime
from src.models.article import Article

class TestArticle:
    
    def test_article_creation(self):
        """Article インスタンスの作成テスト"""
        article = Article(
            title="Test Article",
            url="https://example.com",
            summary="Test summary",
            published_at=datetime.now(),
            source="test"
        )
        
        assert article.title == "Test Article"
        assert article.url == "https://example.com"
        assert article.source == "test"
        assert article.content_hash is not None
        assert len(article.content_hash) == 16
    
    def test_to_dynamodb_item(self):
        """DynamoDB アイテム変換テスト"""
        article = Article(
            title="Test Article",
            url="https://example.com",
            summary="Test summary",
            published_at=datetime(2024, 1, 1, 12, 0, 0),
            source="test"
        )
        
        item = article.to_dynamodb_item()
        
        assert item['date'] == '2024-01-01'
        assert item['title'] == 'Test Article'
        assert item['url'] == 'https://example.com'
        assert item['source'] == 'test'
        assert 'ttl' in item
```

```python
# tests/unit/test_rss_collector.py
import pytest
from unittest.mock import patch, Mock
from src.collectors.rss_collector import RSSCollector

class TestRSSCollector:
    
    def test_collect_success(self):
        """RSS収集成功テスト"""
        collector = RSSCollector()
        
        # モックレスポンス
        mock_response = Mock()
        mock_response.content = '''<?xml version="1.0"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>Test Article</title>
                    <link>https://example.com</link>
                    <description>Test description</description>
                    <pubDate>Mon, 01 Jan 2024 12:00:00 GMT</pubDate>
                </item>
            </channel>
        </rss>'''
        
        with patch('requests.get', return_value=mock_response):
            articles = collector.collect()
            
        assert len(articles) > 0
        assert articles[0].title == "Test Article"
        assert articles[0].url == "https://example.com"
        assert articles[0].source in ["hackernews", "techcrunch", "zenn", "qiita"]
```

#### 8.2 統合テスト

```python
# tests/integration/test_lambda_handlers.py
import pytest
import json
import boto3
from moto import mock_dynamodb
from lambda_functions.collector_handler import handler as collector_handler
from lambda_functions.notifier_handler import handler as notifier_handler

@mock_dynamodb
class TestLambdaHandlers:
    
    def setup_method(self):
        """テスト用DynamoDBテーブル作成"""
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        table = dynamodb.create_table(
            TableName='tech-news-bot-articles-test',
            KeySchema=[
                {'AttributeName': 'date', 'KeyType': 'HASH'},
                {'AttributeName': 'article_id', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'date', 'AttributeType': 'S'},
                {'AttributeName': 'article_id', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # 環境変数設定
        import os
        os.environ['DYNAMODB_TABLE'] = 'tech-news-bot-articles-test'
    
    def test_collector_handler(self):
        """Collector ハンドラーテスト"""
        event = {}
        context = Mock()
        context.aws_request_id = 'test-request-id'
        
        # RSS収集をモック
        with patch('src.collectors.rss_collector.RSSCollector.collect') as mock_collect:
            from src.models.article import Article
            from datetime import datetime
            
            mock_collect.return_value = [
                Article(
                    title="Test Article",
                    url="https://example.com",
                    summary="Test summary",
                    published_at=datetime.now(),
                    source="test"
                )
            ]
            
            response = collector_handler(event, context)
            
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['saved_count'] > 0
```

### Step 9: ローカル開発・テスト

#### 9.1 ローカル実行スクリプト

```python
# scripts/local_test.py
#!/usr/bin/env python3
"""ローカルテスト用スクリプト"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.collectors.rss_collector import RSSCollector
from src.notifiers.slack_notifier import SlackNotifier
from src.utils.logger import setup_logging

def test_rss_collection():
    """RSS収集テスト"""
    print("=== RSS Collection Test ===")
    
    collector = RSSCollector()
    articles = collector.collect()
    
    print(f"Collected {len(articles)} articles:")
    for i, article in enumerate(articles[:5], 1):
        print(f"{i}. {article.title}")
        print(f"   Source: {article.source}, Score: {article.score:.2f}")
        print(f"   URL: {article.url}")
        print()

def test_slack_notification():
    """Slack通知テスト"""
    print("=== Slack Notification Test ===")
    
    # テスト用記事作成
    from src.models.article import Article
    from datetime import datetime
    
    test_articles = [
        Article(
            title="Test Article 1",
            url="https://example.com/1",
            summary="This is a test article for Slack notification",
            published_at=datetime.now(),
            source="test",
            score=0.8
        ),
        Article(
            title="Test Article 2",
            url="https://example.com/2",
            summary="Another test article with different content",
            published_at=datetime.now(),
            source="test",
            score=0.7
        )
    ]
    
    notifier = SlackNotifier()
    success = notifier.send_daily_summary(test_articles, "🧪 Test Notification")
    
    if success:
        print("✅ Slack notification sent successfully")
    else:
        print("❌ Slack notification failed")

def main():
    setup_logging()
    
    print("Tech News Bot - Local Test")
    print("=" * 40)
    
    # 環境変数チェック
    required_env = ['DYNAMODB_TABLE']
    missing_env = [env for env in required_env if not os.getenv(env)]
    
    if missing_env:
        print(f"❌ Missing environment variables: {missing_env}")
        return
    
    try:
        test_rss_collection()
        test_slack_notification()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
```

#### 9.2 環境設定スクリプト

```bash
#!/bin/bash
# scripts/setup_env.sh

echo "Setting up development environment..."

# Python 仮想環境作成
python3 -m venv venv
source venv/bin/activate

# 依存関係インストール
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 環境変数設定
export DYNAMODB_TABLE="tech-news-bot-articles-dev"
export STAGE="dev"
export LOG_LEVEL="DEBUG"

echo "Environment setup completed!"
echo "Run 'source venv/bin/activate' to activate the virtual environment"
```

### Step 10: 初期デプロイと動作確認

#### 10.1 初回デプロイ

```bash
# 1. 依存関係インストール
npm install

# 2. 開発環境にデプロイ
serverless deploy --stage dev

# 3. 手動実行テスト
serverless invoke --function collector --stage dev

# 4. ログ確認
serverless logs --function collector --stage dev
```

#### 10.2 動作確認チェックリスト

1. **RSS収集機能**
   - [ ] 各RSSフィードからの記事取得
   - [ ] 記事データの正常な解析
   - [ ] DynamoDBへの保存

2. **Slack通知機能**
   - [ ] 記事データの取得
   - [ ] Slackメッセージの作成
   - [ ] Webhook経由での送信

3. **エラーハンドリング**
   - [ ] ネットワークエラー時の動作
   - [ ] 無効なデータの処理
   - [ ] ログ出力の確認

これでMVPの実装が完了です。次のフェーズでGitHub API、Reddit API、AI統合などを順次追加していきます。