# Tech News Bot - テック情報収集・通知システム

## 概要

テック情報を自動収集し、Slackチャンネルに定期通知する**完全無料**のGitHub Actionsアプリケーション。X API の代替として RSS フィード、GitHub API、Reddit API を活用してコスト効率的に運用します。

## システム要件

### 機能要件
- テック情報の自動収集（RSS、GitHub、Reddit）
- 重複除去・内容フィルタリング
- Slack通知（1日2回：朝10時、夕方19時）
- 記事の重要度判定・要約機能

### 非機能要件
- **可用性**: 99.5%（GitHub Actions）
- **実行時間**: 収集処理 < 10分（GitHub Actions制限内）
- **コスト**: 完全無料（GitHub Actions 2,000分/月以内）
- **セキュリティ**: GitHub Secrets、HTTPS通信

## アーキテクチャ

### システム構成図

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ GitHub Actions  │───▶│ Python Script    │───▶│ Data Sources    │
│ (Cron Schedule) │    │ (Collector)      │    │ - RSS Feeds     │
└─────────────────┘    └──────────────────┘    │ - GitHub API    │
                                ▼               │ - Reddit API    │
                       ┌──────────────────┐    └─────────────────┘
                       │ Content Filter   │
                       │ & Deduplication  │
                       │ (In-Memory)      │
                       └──────────────────┘
                                ▼
                       ┌──────────────────┐
                       │ Article          │
                       │ Processing       │
                       │ (Score & Format) │
                       └──────────────────┘
                                ▼
                       ┌──────────────────┐
                       │ Slack Webhook    │
                       │ (Direct Send)    │
                       └──────────────────┘
```

### データソース戦略

**RSS/Atom Feeds:**
- Hacker News
- TechCrunch Japan
- Ars Technica
- The Verge
- Zenn（日本語）
- Qiita（日本語）

**API連携:**
- GitHub Trending（リポジトリトレンド）
- Reddit r/programming, r/webdev
- Stack Overflow（人気質問）

**X API代替理由:**
- X API v2は月額$100〜と高コスト
- RSS/APIの組み合わせで十分な情報量を確保
- GitHub Actionsで完全無料運用が可能

## プロジェクト構成

```
tech-news-bot/
├── .github/
│   └── workflows/
│       └── collect-news.yml    # GitHub Actionsワークフロー
├── src/
│   ├── collectors/             # データ収集モジュール
│   │   ├── __init__.py
│   │   ├── base_collector.py
│   │   ├── rss_collector.py
│   │   ├── github_collector.py
│   │   └── reddit_collector.py
│   ├── processors/             # データ処理モジュール
│   │   ├── __init__.py
│   │   ├── deduplicator.py
│   │   ├── content_filter.py
│   │   └── article_processor.py
│   ├── notifiers/              # 通知処理モジュール
│   │   ├── __init__.py
│   │   └── slack_notifier.py
│   ├── models/                 # データモデル
│   │   ├── __init__.py
│   │   └── article.py
│   └── utils/                  # ユーティリティ
│       ├── __init__.py
│       ├── config.py
│       └── logger.py
├── main.py                     # メインスクリプト
├── tests/                      # テストコード
│   ├── unit/
│   └── integration/
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

## データモデル

### Article クラス

```python
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

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
        return {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{self.title}*\n{self.summary}"
                    },
                    "accessory": {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Read More"},
                        "url": self.url
                    }
                }
            ]
        }
```

### データ永続化

GitHub Actionsはステートレスなため、長期的なデータ保存は行いません。
代わりに以下の軽量な重複チェック機能を実装：

```python
# 実行時メモリ内での重複チェック
seen_urls = set()
seen_content_hashes = set()

def is_duplicate(article: Article) -> bool:
    """同一実行内での重複チェック"""
    url_hash = hashlib.md5(article.url.encode()).hexdigest()
    content_hash = article.content_hash
    
    if url_hash in seen_urls or content_hash in seen_content_hashes:
        return True
    
    seen_urls.add(url_hash)
    seen_content_hashes.add(content_hash)
    return False
```

## インフラストラクチャ

### GitHub Actions 構成

```yaml
# .github/workflows/collect-news.yml
name: Tech News Collection

on:
  schedule:
    - cron: '0 1 * * *'    # 10:00 JST (毎日)
    - cron: '0 10 * * *'   # 19:00 JST (毎日)
  workflow_dispatch:       # 手動実行可能

jobs:
  collect-and-notify:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    
    steps:
    - name: Checkout repository
      uses: actions/checkout@v4
      
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
        cache: 'pip'
        
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        
    - name: Run news collection
      env:
        SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        REDDIT_CLIENT_ID: ${{ secrets.REDDIT_CLIENT_ID }}
        REDDIT_CLIENT_SECRET: ${{ secrets.REDDIT_CLIENT_SECRET }}
      run: |
        python main.py
        
    - name: Upload logs (on failure)
      if: failure()
      uses: actions/upload-artifact@v3
      with:
        name: error-logs
        path: logs/
        retention-days: 7
```

### 必要な GitHub 設定

- **Repository Secrets**: API キーの安全な管理
  - `SLACK_WEBHOOK_URL`: Slack Incoming Webhook URL
  - `GITHUB_TOKEN`: GitHub Personal Access Token（任意）
  - `REDDIT_CLIENT_ID`: Reddit API Client ID
  - `REDDIT_CLIENT_SECRET`: Reddit API Client Secret
- **GitHub Actions**: 月2,000分まで無料（1日2回×10分 = 月600分程度使用）

## 実装仕様

### 収集処理フロー

**main.py - 統合処理**
```python
def main():
    """メインの記事収集・通知処理"""
    logger.info("Starting tech news collection")
    
    # 各データソースから記事を収集
    collectors = [
        RSSCollector(),
        GitHubCollector(),
        RedditCollector()
    ]
    
    all_articles = []
    for collector in collectors:
        try:
            articles = collector.collect()
            all_articles.extend(articles)
            logger.info(f"Collected {len(articles)} articles from {collector.source}")
        except Exception as e:
            logger.error(f"Failed to collect from {collector.source}: {e}")
    
    # 重複除去（同一実行内）
    deduplicator = Deduplicator()
    unique_articles = deduplicator.remove_duplicates(all_articles)
    
    # コンテンツフィルタリング
    content_filter = ContentFilter()
    filtered_articles = content_filter.filter(unique_articles)
    
    # 記事処理（スコアリング・フォーマット）
    processor = ArticleProcessor()
    processed_articles = processor.process(filtered_articles)
    
    # 上位記事のみ選択
    top_articles = sorted(processed_articles, key=lambda x: x.score, reverse=True)[:10]
    
    # Slack通知
    if top_articles:
        slack_notifier = SlackNotifier()
        success = slack_notifier.send_daily_summary(top_articles)
        
        if success:
            logger.info(f"Successfully sent {len(top_articles)} articles to Slack")
        else:
            logger.error("Failed to send Slack notification")
            sys.exit(1)
    else:
        logger.info("No articles to notify")

if __name__ == "__main__":
    main()
```

### RSS収集実装

```python
import feedparser
from datetime import datetime, timedelta
from typing import List

class RSSCollector(BaseCollector):
    """RSS/Atom フィード収集クラス"""
    
    RSS_FEEDS = [
        {"url": "https://hnrss.org/frontpage", "source": "hackernews"},
        {"url": "https://japan.techcrunch.com/feed/", "source": "techcrunch"},
        {"url": "https://zenn.dev/feed", "source": "zenn"},
        {"url": "https://qiita.com/popular-items/feed", "source": "qiita"},
    ]
    
    def collect(self) -> List[Article]:
        """RSSフィードから記事を収集"""
        articles = []
        cutoff_time = datetime.now() - timedelta(hours=12)  # 12時間以内の記事のみ
        
        for feed_config in self.RSS_FEEDS:
            try:
                feed = feedparser.parse(feed_config["url"])
                
                for entry in feed.entries:
                    published_time = self._parse_published_time(entry)
                    
                    if published_time < cutoff_time:
                        continue
                    
                    article = Article(
                        title=entry.title,
                        url=entry.link,
                        summary=self._extract_summary(entry),
                        published_at=published_time,
                        source=feed_config["source"],
                        tags=self._extract_tags(entry),
                        score=self._calculate_score(entry),
                        content_hash=self._generate_content_hash(entry.title, entry.link)
                    )
                    
                    articles.append(article)
                    
            except Exception as e:
                self.logger.error(f"Failed to parse RSS feed {feed_config['url']}: {e}")
        
        return articles
```

## 運用・監視

### GitHub Actions監視

```python
import logging

# シンプルなログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# 実行結果のログ出力
logger.info(f"Collected {len(articles)} articles from {source}")
logger.info(f"Successfully sent {len(top_articles)} articles to Slack")
```

GitHub Actionsの実行履歴とログで監視可能：
- **実行状況**: Actions タブで成功/失敗を確認
- **詳細ログ**: 各ステップの実行ログを確認
- **アラート**: 実行失敗時にメール通知（GitHub設定）

## コスト見積もり

### 月額運用コスト

| 項目 | 使用量 | 月額料金 |
|------|--------|----------|
| GitHub Actions | 60回実行 × 10分 = 600分 | **$0** (無料枠2,000分) |
| GitHub Repository | 1個（プライベート可） | **$0** |
| API使用料 | RSS(無料) + GitHub(無料) + Reddit(無料) | **$0** |
| **合計** | | **完全無料** |

## セキュリティ

### セキュリティ対策

1. **機密情報管理**
   - GitHub Secrets での API キー管理
   - 環境変数経由での安全な参照

2. **ネットワークセキュリティ**  
   - HTTPS通信の強制
   - GitHub Actions の secure runner 環境

3. **アクセス制御**
   - Repository のアクセス権限管理
   - Personal Access Token の適切なスコープ設定

## セットアップ

### 1. リポジトリ準備

```bash
# リポジトリをクローン
git clone <your-repo-url>
cd tech-news-bot

# Python 仮想環境作成（ローカル開発用）
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係インストール
pip install -r requirements.txt
```

### 2. GitHub Secrets設定

Repository Settings > Secrets and variables > Actions で以下を設定：

```
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
```

### 3. Slack Webhook URL取得

1. Slack App管理画面で新しいアプリを作成
2. "Incoming Webhooks" を有効化
3. 通知先チャンネルを選択してWebhook URLを取得
4. GitHub SecretsのSLACK_WEBHOOK_URLに設定

### 4. 動作確認

```bash
# ローカルでテスト実行
python main.py

# GitHub Actions手動実行
# Repository > Actions > "Tech News Collection" > "Run workflow"
```

## 実装フェーズ

### Phase 1: 基本機能 (1週間)
- RSS収集機能
- 基本的なフィルタリング  
- Slack通知機能
- GitHub Actions設定

### Phase 2: 機能拡張 (1週間)
- GitHub API連携
- Reddit API連携
- 重複除去の改善
- スコアリング機能

### Phase 3: 最適化 (継続的)
- 記事の品質改善
- 通知内容の最適化
- エラーハンドリング強化

## まとめ

**GitHub Actions版の主なメリット:**

1. **完全無料**: 月額$0での運用
2. **シンプル**: AWS設定不要、GitHub上で完結
3. **自動化**: 完全自動での情報収集・配信  
4. **拡張性**: 新しいデータソースの容易な追加
5. **透明性**: 実行履歴とログが GitHub で管理

X API の代替として、RSS・GitHub・Reddit を組み合わせることで、十分な情報量と品質を確保しながら、**完全無料**での運用を実現する設計となっています。