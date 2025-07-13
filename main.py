#!/usr/bin/env python3

import sys
import os
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.collectors.rss_collector import RSSCollector
from src.collectors.github_collector import GitHubCollector
from src.collectors.reddit_collector import RedditCollector
from src.processors.article_processor import ArticleProcessor
from src.notifiers.slack_notifier import SlackNotifier
from src.utils.config import Config
from src.utils.logger import setup_logger, CollectionStats


def main():
    """メインの記事収集・通知処理"""
    logger = setup_logger("main")
    stats = CollectionStats()
    
    logger.info("=== Tech News Collection Started ===")
    
    # 設定の検証
    if not Config.validate():
        logger.error("Configuration validation failed")
        sys.exit(1)
    
    try:
        # 各データソースから記事を収集
        logger.info("Starting article collection from all sources")
        
        collectors = [
            ("RSS", RSSCollector()),
            ("GitHub", GitHubCollector()),
            ("Reddit", RedditCollector())
        ]
        
        all_articles = []
        
        for name, collector in collectors:
            try:
                logger.info(f"Collecting from {name}")
                articles = collector.collect()
                all_articles.extend(articles)
                stats.add_source_stats(name.lower(), len(articles))
                logger.info(f"Collected {len(articles)} articles from {name}")
                
            except Exception as e:
                error_msg = f"Failed to collect from {name}: {e}"
                logger.error(error_msg)
                stats.add_error(name.lower(), str(e))
        
        logger.info(f"Total articles collected: {len(all_articles)}")
        
        if not all_articles:
            logger.warning("No articles collected from any source")
            return
        
        # 記事処理（重複除去・フィルタリング）
        logger.info("Processing articles (deduplication and filtering)")
        processor = ArticleProcessor()
        processed_articles = processor.process(all_articles)
        
        stats.total_filtered = len(processed_articles)
        logger.info(f"Articles after processing: {len(processed_articles)}")
        
        if not processed_articles:
            logger.warning("No articles remaining after processing")
            return
        
        # 上位記事のみ選択
        top_articles = processed_articles[:Config.MAX_ARTICLES_PER_NOTIFICATION]
        logger.info(f"Selected top {len(top_articles)} articles for notification")
        
        # Slack通知
        logger.info("Sending notification to Slack")
        slack_notifier = SlackNotifier()
        success = slack_notifier.send_daily_summary(top_articles)
        
        if success:
            stats.set_sent_count(len(top_articles))
            logger.info(f"Successfully sent {len(top_articles)} articles to Slack")
        else:
            logger.error("Failed to send Slack notification")
            sys.exit(1)
    
    except Exception as e:
        error_msg = f"Unexpected error in main process: {e}"
        logger.error(error_msg, exc_info=True)
        
        # エラー通知を送信
        try:
            slack_notifier = SlackNotifier()
            slack_notifier.send_error_notification(error_msg)
        except:
            pass  # エラー通知の失敗は無視
        
        sys.exit(1)
    
    finally:
        # 統計情報をログ出力
        logger.info(stats.get_summary())
        logger.info("=== Tech News Collection Completed ===")


if __name__ == "__main__":
    main()