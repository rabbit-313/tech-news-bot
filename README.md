# Tech News Bot 🤖

テック情報を自動収集し、Slackに通知する**完全無料**のGitHub Actionsアプリケーション

[![GitHub Actions](https://github.com/rabbit-313/tech-news-bot/workflows/Tech%20News%20Collection/badge.svg)](https://github.com/rabbit-313/tech-news-bot/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## ✨ 機能

- 🔄 **自動収集**: RSS、GitHub、Reddit から最新テック情報を収集
- 🎯 **スマートフィルタリング**: 重複除去・品質フィルタリング
- 📱 **Slack通知**: 1日2回（朝10時・夜19時）自動配信
- 💰 **完全無料**: GitHub Actions で運用コスト0円
- ⚡ **簡単セットアップ**: 5分で導入完了

## 🚀 クイックスタート

### 1. リポジトリをフォーク

```bash
# このリポジトリをフォークしてクローン
git clone https://github.com/YOUR_USERNAME/tech-news-bot.git
cd tech-news-bot
```

### 2. Slack Webhook URLを取得

1. [Slack API](https://api.slack.com/apps) で新しいアプリを作成
2. "Incoming Webhooks" を有効化
3. 通知先チャンネルを選択してWebhook URLを取得
4. URLをコピー（後で使用）

### 3. GitHub Secrets設定

Repository Settings → Secrets and variables → Actions で以下を設定：

| Secret名 | 値 | 必須 |
|---------|---|------|
| `SLACK_WEBHOOK_URL` | SlackのWebhook URL | ✅ |
| `REDDIT_CLIENT_ID` | Reddit API Client ID | ⚠️ |
| `REDDIT_CLIENT_SECRET` | Reddit API Secret | ⚠️ |

> ⚠️ Reddit APIは任意です。設定しない場合はRSSとGitHubのみから収集

### 4. 自動実行開始

設定完了後、GitHub Actionsが自動で動作開始：
- **毎日10:00 JST**: 朝の技術ニュース配信
- **毎日19:00 JST**: 夜の技術ニュース配信

## 📊 データソース

- 📰 **RSS**: Hacker News、Zenn、Qiita、VentureBeat
- 🔧 **GitHub**: トレンドリポジトリ（Python、JS、Go、Rust等）
- 💬 **Reddit**: r/programming、r/webdev、r/MachineLearning等

## 🛠️ カスタマイズ

### 通知スケジュール変更

`.github/workflows/collect-news.yml` の cron設定を編集：

```yaml
on:
  schedule:
    - cron: '0 1 * * *'    # 10:00 JST
    - cron: '0 10 * * *'   # 19:00 JST
```

### 収集対象の追加

`src/utils/config.py` でデータソースを追加・変更可能：

```python
RSS_FEEDS = [
    {"url": "https://hnrss.org/frontpage", "source": "hackernews"},
    {"url": "https://your-rss-feed.com/feed", "source": "your_source"},
]
```

## 🔧 手動実行

GitHub Actions画面から手動実行も可能：
1. Actions タブ → "Tech News Collection"
2. "Run workflow" ボタンをクリック

## 🎯 Reddit API設定（任意）

より多くのソースから情報収集したい場合：

### 1. Reddit アプリケーション作成

1. [Reddit App Preferences](https://www.reddit.com/prefs/apps) にアクセス
2. "Create App" → "script" を選択
3. Client IDとClient Secretをコピー

### 2. GitHub Secretsに追加

```
REDDIT_CLIENT_ID: あなたのClient ID
REDDIT_CLIENT_SECRET: あなたのClient Secret
```

## 🐛 トラブルシューティング

### GitHub Actions が動作しない

1. **Repository Settings** → **Actions** → **General**
2. "Allow all actions and reusable workflows" を選択
3. **Workflow permissions** で "Read and write permissions" を選択

### Slack通知が届かない

1. Webhook URLが正しく設定されているか確認
2. Slackアプリがチャンネルに追加されているか確認
3. GitHub Actions のログでエラーを確認

## 📊 モニタリング

### 実行状況の確認

1. **Actions タブ**: ワークフローの実行履歴
2. **詳細ログ**: エラーや収集状況を確認
3. **Slack通知**: 実行結果がSlackに配信

### パフォーマンス

- **実行時間**: 約5-10分
- **使用リソース**: GitHub Actions無料枠内
- **収集記事数**: 通常10-50記事/回

## 🤝 コントリビューション

1. このリポジトリをフォーク
2. 機能ブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. Pull Requestを作成

## 📄 ライセンス

MIT License - 詳細は [LICENSE](LICENSE) ファイルを参照

## ⭐ 謝辞

- [feedparser](https://feedparser.readthedocs.io/) - RSS/Atom フィード解析
- [PRAW](https://praw.readthedocs.io/) - Reddit API
- [PyGithub](https://pygithub.readthedocs.io/) - GitHub API
- GitHub Actions - 無料の自動実行環境

---

**🚀 Tech News Botであなたのチームの技術情報収集を自動化しましょう！**