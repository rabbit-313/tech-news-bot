# Tech News Bot - デプロイメントガイド

## 前提条件

### 必要なツール・アカウント

1. **AWS アカウント**
   - AWS CLI がインストール・設定済み
   - 適切な IAM 権限（Lambda、DynamoDB、CloudWatch、SSM の操作権限）

2. **開発環境**
   - Python 3.11+
   - Node.js 18+ (Serverless Framework用)
   - Git

3. **外部サービス**
   - Slack ワークスペース（Webhook URL）
   - GitHub Personal Access Token
   - Reddit API アクセス（Client ID/Secret）
   - OpenAI API キー

## セットアップ手順

### 1. リポジトリのクローンと環境構築

```bash
# リポジトリクローン
git clone <repository-url>
cd tech-news-bot

# Python 仮想環境作成
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係インストール
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Serverless Framework セットアップ
npm install -g serverless
npm install
```

### 2. AWS CLI 設定

```bash
# AWS 認証情報設定
aws configure
# または環境変数で設定
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=ap-northeast-1
```

### 3. API キー・シークレットの設定

#### 3.1 Slack Webhook URL の取得

1. Slack ワークスペースで新しいアプリを作成
2. Incoming Webhooks を有効化
3. 対象チャンネルにWebhookを追加
4. Webhook URL をコピー

#### 3.2 GitHub Personal Access Token の作成

1. GitHub Settings > Developer settings > Personal access tokens
2. "Generate new token (classic)" をクリック
3. 必要なスコープを選択：
   - `public_repo` (パブリックリポジトリアクセス)
   - `read:org` (組織情報の読み取り)
4. トークンを生成してコピー

#### 3.3 Reddit API アクセス設定

1. Reddit の [App Preferences](https://www.reddit.com/prefs/apps) にアクセス
2. "Create App" をクリック
3. アプリタイプを "script" に設定
4. Client ID と Client Secret をコピー

#### 3.4 OpenAI API キー取得

1. [OpenAI Platform](https://platform.openai.com/) にアクセス
2. API Keys セクションで新しいキーを作成
3. API キーをコピー

### 4. AWS SSM Parameter Store への設定保存

```bash
# Slack Webhook URL
aws ssm put-parameter \
  --name "/tech-news-bot/slack-webhook-url" \
  --value "https://hooks.slack.com/services/YOUR/WEBHOOK/URL" \
  --type "SecureString" \
  --description "Slack Incoming Webhook URL"

# GitHub Token
aws ssm put-parameter \
  --name "/tech-news-bot/github-token" \
  --value "ghp_your_github_token" \
  --type "SecureString" \
  --description "GitHub Personal Access Token"

# Reddit Client ID
aws ssm put-parameter \
  --name "/tech-news-bot/reddit-client-id" \
  --value "your_reddit_client_id" \
  --type "SecureString" \
  --description "Reddit API Client ID"

# Reddit Client Secret
aws ssm put-parameter \
  --name "/tech-news-bot/reddit-client-secret" \
  --value "your_reddit_client_secret" \
  --type "SecureString" \
  --description "Reddit API Client Secret"

# OpenAI API Key
aws ssm put-parameter \
  --name "/tech-news-bot/openai-api-key" \
  --value "sk-your_openai_api_key" \
  --type "SecureString" \
  --description "OpenAI API Key"
```

### 5. 設定ファイルの編集

#### 5.1 serverless.yml の環境固有設定

```yaml
# serverless.yml (抜粋)
custom:
  stage: ${opt:stage, 'dev'}
  region: ${opt:region, 'ap-northeast-1'}
  
  # ステージ別設定
  config:
    dev:
      schedule_enabled: false  # 開発環境では手動実行
      log_level: DEBUG
    prod:
      schedule_enabled: true   # 本番環境では自動実行
      log_level: INFO

provider:
  stage: ${self:custom.stage}
  region: ${self:custom.region}
  environment:
    STAGE: ${self:custom.stage}
    LOG_LEVEL: ${self:custom.config.${self:custom.stage}.log_level}

functions:
  collector:
    events:
      - schedule: 
          rate: cron(0 1,10 * * ? *)
          enabled: ${self:custom.config.${self:custom.stage}.schedule_enabled}
```

#### 5.2 設定値の検証

```bash
# 設定値確認スクリプト
python scripts/verify_config.py
```

## デプロイメント

### 1. 開発環境デプロイ

```bash
# 開発環境にデプロイ
serverless deploy --stage dev

# デプロイ後の動作確認
serverless invoke --function collector --stage dev
serverless invoke --function notifier --stage dev

# ログ確認
serverless logs --function collector --stage dev --tail
```

### 2. 本番環境デプロイ

```bash
# 本番環境にデプロイ
serverless deploy --stage prod

# CloudWatch でスケジュール実行を確認
aws events list-rules --region ap-northeast-1
```

### 3. 特定関数のみデプロイ

```bash
# Collector 関数のみ更新
serverless deploy function --function collector --stage prod

# Notifier 関数のみ更新
serverless deploy function --function notifier --stage prod
```

## 環境別設定

### 開発環境 (dev)

```yaml
# config/dev.yml
schedule_enabled: false
log_level: DEBUG
min_article_score: 0.3
max_articles_per_notification: 15
collection_sources:
  - rss
  - github
# reddit は開発時は無効（API制限回避）

notification_schedule:
  enabled: false  # 手動実行のみ
```

### ステージング環境 (staging)

```yaml
# config/staging.yml
schedule_enabled: true
log_level: INFO
min_article_score: 0.5
max_articles_per_notification: 12
collection_sources:
  - rss
  - github
  - reddit

notification_schedule:
  enabled: true
  # 本番より頻度を下げる
  cron: "cron(0 9,18 * * ? *)"  # 1日2回
```

### 本番環境 (prod)

```yaml
# config/prod.yml
schedule_enabled: true
log_level: INFO
min_article_score: 0.6
max_articles_per_notification: 10
collection_sources:
  - rss
  - github
  - reddit

notification_schedule:
  enabled: true
  cron: "cron(0 1,10 * * ? *)"  # 10:00, 19:00 JST

monitoring:
  alerts_enabled: true
  error_threshold: 1
  no_articles_threshold: 5
```

## 設定値管理

### 環境変数一覧

| 変数名 | 説明 | 必須 | デフォルト値 |
|--------|------|------|-------------|
| `STAGE` | デプロイ環境 | Yes | - |
| `LOG_LEVEL` | ログレベル | No | INFO |
| `DYNAMODB_TABLE` | DynamoDB テーブル名 | Yes | - |
| `SLACK_WEBHOOK_URL` | Slack Webhook URL | Yes | - |
| `GITHUB_TOKEN` | GitHub Token | Yes | - |
| `REDDIT_CLIENT_ID` | Reddit Client ID | Yes | - |
| `REDDIT_CLIENT_SECRET` | Reddit Client Secret | Yes | - |
| `OPENAI_API_KEY` | OpenAI API Key | Yes | - |

### SSM Parameter の命名規則

```
/tech-news-bot/{stage}/{parameter-name}

例:
/tech-news-bot/dev/slack-webhook-url
/tech-news-bot/prod/github-token
```

### 設定値の更新

```bash
# 本番環境の Slack Webhook URL を更新
aws ssm put-parameter \
  --name "/tech-news-bot/prod/slack-webhook-url" \
  --value "https://hooks.slack.com/services/NEW/WEBHOOK/URL" \
  --type "SecureString" \
  --overwrite

# 更新後は Lambda 関数を再起動（環境変数を再読み込み）
serverless deploy function --function collector --stage prod
serverless deploy function --function notifier --stage prod
```

## トラブルシューティング

### よくある問題と解決策

#### 1. Lambda 実行エラー

**症状**: Lambda 関数が失敗する

**確認手順**:
```bash
# ログ確認
serverless logs --function collector --stage prod --startTime 1h

# CloudWatch でエラー詳細確認
aws logs filter-log-events \
  --log-group-name "/aws/lambda/tech-news-bot-prod-collector" \
  --start-time $(date -d '1 hour ago' +%s)000
```

**一般的な解決策**:
- IAM 権限の確認
- SSM Parameter の存在確認
- タイムアウト設定の見直し
- メモリ使用量の確認

#### 2. DynamoDB アクセスエラー

**症状**: `AccessDeniedException` エラー

**解決策**:
```bash
# IAM ポリシーの確認
aws iam list-attached-role-policies --role-name tech-news-bot-prod-ap-northeast-1-lambdaRole

# DynamoDB テーブルの存在確認
aws dynamodb describe-table --table-name tech-news-bot-articles-prod
```

#### 3. Slack 通知失敗

**症状**: Slack チャンネルに通知が届かない

**確認手順**:
```bash
# Webhook URL の確認
aws ssm get-parameter --name "/tech-news-bot/prod/slack-webhook-url" --with-decryption

# 手動テスト
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"Test message"}' \
  YOUR_WEBHOOK_URL
```

#### 4. API レート制限

**症状**: GitHub/Reddit API で 429 エラー

**解決策**:
- リクエスト間隔の調整
- API キーの確認
- 使用量制限の確認

```python
# レート制限対応の実装例
import time
from functools import wraps

def rate_limit(calls_per_minute=60):
    def decorator(func):
        last_called = [0.0]
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            left_to_wait = 60.0 / calls_per_minute - elapsed
            
            if left_to_wait > 0:
                time.sleep(left_to_wait)
            
            ret = func(*args, **kwargs)
            last_called[0] = time.time()
            return ret
        
        return wrapper
    return decorator
```

### ログ分析

#### CloudWatch Insights クエリ例

```sql
-- エラー分析
fields @timestamp, @message, error
| filter @message like /ERROR/
| sort @timestamp desc
| limit 20

-- 処理時間分析
fields @timestamp, @duration
| filter @type = "REPORT"
| stats avg(@duration), max(@duration), min(@duration) by bin(5m)

-- API 呼び出し分析
fields @timestamp, source, articles_collected
| filter @message like /collection_completed/
| stats sum(articles_collected) by source
```

#### メトリクス監視

```bash
# カスタムメトリクスの確認
aws cloudwatch get-metric-statistics \
  --namespace "TechNewsBot/Collection" \
  --metric-name "ArticlesCollected" \
  --start-time $(date -d '24 hours ago' --iso-8601) \
  --end-time $(date --iso-8601) \
  --period 3600 \
  --statistics Sum \
  --dimensions Name=Source,Value=github
```

## 運用・メンテナンス

### 定期メンテナンス

#### 1. 月次タスク

```bash
# DynamoDB 使用量確認
aws dynamodb describe-table --table-name tech-news-bot-articles-prod \
  --query 'Table.TableSizeBytes'

# CloudWatch コスト確認
aws cloudwatch get-metric-statistics \
  --namespace "AWS/Lambda" \
  --metric-name "Duration" \
  --dimensions Name=FunctionName,Value=tech-news-bot-prod-collector \
  --start-time $(date -d '1 month ago' --iso-8601) \
  --end-time $(date --iso-8601) \
  --period 86400 \
  --statistics Sum
```

#### 2. 四半期タスク

- 依存関係の更新
- セキュリティパッチの適用
- パフォーマンス分析とチューニング

```bash
# パッケージ更新
pip list --outdated
pip install -U package_name

# セキュリティ監査
pip audit

# デプロイ
serverless deploy --stage prod
```

### バックアップとリストア

#### DynamoDB バックアップ

```bash
# 手動バックアップ作成
aws dynamodb create-backup \
  --table-name tech-news-bot-articles-prod \
  --backup-name "manual-backup-$(date +%Y%m%d)"

# 自動バックアップ設定
aws dynamodb put-backup-policy \
  --table-name tech-news-bot-articles-prod \
  --backup-policy-description "Daily backup at 3 AM JST" \
  --backup-policy '{
    "BackupPolicy": {
      "BackupPolicyName": "DailyBackup",
      "BackupPolicyDescription": "Daily backup",
      "BackupRetentionPeriodInDays": 30,
      "BackupCreationDateTime": "2024-01-01T03:00:00.000Z",
      "BackupTypeFilter": ["FULL"]
    }
  }'
```

### スケーリング対応

#### Lambda 同時実行数制限

```yaml
# serverless.yml
functions:
  collector:
    reservedConcurrency: 5  # 最大5個の同時実行
    
  notifier:
    reservedConcurrency: 2  # 最大2個の同時実行
```

#### DynamoDB オートスケーリング

```yaml
resources:
  Resources:
    ArticlesTable:
      Type: AWS::DynamoDB::Table
      Properties:
        BillingMode: ON_DEMAND  # オンデマンド課金でオートスケーリング
        # または
        BillingMode: PROVISIONED
        ProvisionedThroughput:
          ReadCapacityUnits: 5
          WriteCapacityUnits: 5
```

### セキュリティ更新

#### 1. IAM ポリシーの最小権限確認

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:Query",
        "dynamodb:UpdateItem"
      ],
      "Resource": "arn:aws:dynamodb:ap-northeast-1:*:table/tech-news-bot-articles-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ssm:GetParameter"
      ],
      "Resource": "arn:aws:ssm:ap-northeast-1:*:parameter/tech-news-bot/*"
    }
  ]
}
```

#### 2. API キーローテーション

```bash
# GitHub Token 更新
NEW_TOKEN="ghp_new_github_token"
aws ssm put-parameter \
  --name "/tech-news-bot/prod/github-token" \
  --value "$NEW_TOKEN" \
  --type "SecureString" \
  --overwrite

# Lambda 関数再起動
serverless deploy function --function collector --stage prod
```

このデプロイメントガイドに従うことで、安全で効率的なテックニュース収集システムを本番環境で運用できます。