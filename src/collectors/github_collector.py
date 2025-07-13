import requests
from datetime import datetime, timedelta
from typing import List, Optional
import time

from .base_collector import BaseCollector
from ..models.article import Article
from ..utils.config import Config


class GitHubCollector(BaseCollector):
    """GitHub トレンドリポジトリ収集クラス"""
    
    def __init__(self):
        super().__init__("github")
        self.token = Config.GITHUB_TOKEN
        self.base_url = "https://api.github.com"
        self.session = requests.Session()
        
        # Authorizationヘッダーを設定（トークンがある場合）
        if self.token:
            self.session.headers.update({
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json"
            })
    
    def collect(self) -> List[Article]:
        """GitHubから人気リポジトリを収集"""
        all_articles = []
        
        # 各言語のトレンドリポジトリを取得
        for language in Config.GITHUB_TRENDING_LANGUAGES:
            try:
                self.logger.info(f"Fetching GitHub trending for: {language}")
                articles = self._collect_trending_repos(language)
                all_articles.extend(articles)
                self.logger.info(f"Collected {len(articles)} repos for {language}")
                
                # API制限対策
                time.sleep(2)
                
            except Exception as e:
                self.logger.error(f"Failed to fetch GitHub trending for {language}: {e}")
        
        return all_articles
    
    def _collect_trending_repos(self, language: Optional[str] = None) -> List[Article]:
        """特定言語のトレンドリポジトリを収集"""
        articles = []
        
        # 過去24時間で作成またはプッシュされたリポジトリを検索
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        query_parts = [
            f"created:>{yesterday}",
            "stars:>10"  # 最低10スター
        ]
        
        if language:
            query_parts.append(f"language:{language}")
        
        query = " ".join(query_parts)
        
        try:
            url = f"{self.base_url}/search/repositories"
            params = {
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": 20  # 上位20個
            }
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            for repo in data.get("items", []):
                try:
                    article = self._create_article_from_repo(repo)
                    if article:
                        articles.append(article)
                except Exception as e:
                    self.logger.error(f"Failed to process repo {repo.get('name', 'unknown')}: {e}")
            
        except Exception as e:
            self.logger.error(f"Failed to fetch trending repos for {language}: {e}")
        
        return articles
    
    def _create_article_from_repo(self, repo: dict) -> Optional[Article]:
        """リポジトリデータから記事を作成"""
        try:
            # 基本情報
            name = repo.get("name", "")
            full_name = repo.get("full_name", "")
            description = repo.get("description", "")
            url = repo.get("html_url", "")
            stars = repo.get("stargazers_count", 0)
            language = repo.get("language", "")
            
            # 公開日時
            created_at = datetime.fromisoformat(
                repo.get("created_at", "").replace("Z", "+00:00")
            )
            
            # 更新日時も考慮
            updated_at = datetime.fromisoformat(
                repo.get("updated_at", "").replace("Z", "+00:00")
            )
            
            # より最近の日時を使用
            published_at = max(created_at, updated_at)
            
            # 古すぎる場合はスキップ
            if not self._is_recent(published_at, Config.HOURS_LOOKBACK):
                return None
            
            # タイトルと概要を作成
            title = f"{full_name}: {name}"
            if description:
                summary = description
            else:
                summary = f"New {language} repository"
            
            # スコア計算
            score = self._calculate_score(
                title=title,
                summary=summary,
                stars=stars
            )
            
            # タグ抽出
            tags = self._extract_tags(title, summary)
            if language:
                tags.append(language.lower())
            
            article = Article(
                title=self._clean_text(title),
                url=url,
                summary=self._clean_text(summary),
                published_at=published_at,
                source="github",
                tags=tags,
                score=score,
                content_hash="",  # __post_init__で生成される
                author=repo.get("owner", {}).get("login", None)
            )
            
            return article
            
        except Exception as e:
            self.logger.error(f"Failed to create article from repo data: {e}")
            return None