import logging
import sys
from datetime import datetime
from typing import Optional


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """ロガーをセットアップ"""
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 既存のハンドラーがある場合は削除
    if logger.handlers:
        logger.handlers.clear()
    
    # フォーマッター作成
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # コンソールハンドラー
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger


# デフォルトロガー
logger = setup_logger(__name__)


class CollectionStats:
    """収集統計クラス"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.sources = {}
        self.total_collected = 0
        self.total_filtered = 0
        self.total_sent = 0
        self.errors = []
    
    def add_source_stats(self, source: str, collected: int, filtered: int = 0):
        """ソース別統計を追加"""
        self.sources[source] = {
            "collected": collected,
            "filtered": filtered
        }
        self.total_collected += collected
        self.total_filtered += filtered
    
    def add_error(self, source: str, error: str):
        """エラーを追加"""
        self.errors.append({
            "source": source,
            "error": error,
            "timestamp": datetime.now()
        })
    
    def set_sent_count(self, count: int):
        """送信数を設定"""
        self.total_sent = count
    
    def get_summary(self) -> str:
        """統計サマリーを取得"""
        duration = datetime.now() - self.start_time
        
        summary = f"""
=== Tech News Collection Summary ===
Duration: {duration.total_seconds():.2f} seconds
Total Collected: {self.total_collected} articles
Total After Filtering: {self.total_filtered} articles  
Total Sent to Slack: {self.total_sent} articles

Source Breakdown:"""
        
        for source, stats in self.sources.items():
            summary += f"\n  {source}: {stats['collected']} collected, {stats['filtered']} after filtering"
        
        if self.errors:
            summary += f"\n\nErrors ({len(self.errors)}):"
            for error in self.errors:
                summary += f"\n  {error['source']}: {error['error']}"
        
        summary += "\n" + "=" * 40
        
        return summary