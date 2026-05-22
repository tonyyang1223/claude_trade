"""GitHub activity analysis module."""
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path

from src.data.models import GithubData
from src.data.cache import DataCache


class GithubAnalyzer:
    """Analyzes GitHub activity for cryptocurrency projects.

    Uses GitHub API (free, 5000 calls/hour).

    Attributes:
        cache: DataCache for caching data
        api_token: Optional GitHub API token for higher rate limits

    Example:
        >>> analyzer = GithubAnalyzer()
        >>> github = analyzer.analyze("bitcoin", "bitcoin/bitcoin")
    """

    GITHUB_API = "https://api.github.com"

    def __init__(self, cache_dir: Path = Path("data/cache"), api_token: Optional[str] = None):
        """Initialize GitHub analyzer.

        Args:
            cache_dir: Directory for caching data
            api_token: Optional GitHub API token
        """
        self.cache = DataCache(cache_dir, expire_hours=6)
        self.api_token = api_token
        self.headers = {}
        if api_token:
            self.headers["Authorization"] = f"token {api_token}"

    def fetch_repo_info(self, owner: str, repo: str) -> Dict[str, Any]:
        """Fetch repository basic information.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            Dictionary with repo info
        """
        cache_key = f"github_repo_{owner}_{repo}"

        cached = self.cache.load(cache_key)
        if cached:
            return cached

        try:
            response = requests.get(
                f"{self.GITHUB_API}/repos/{owner}/{repo}",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            self.cache.save(cache_key, data)

            return data
        except Exception as e:
            print(f"Warning: Failed to fetch repo info: {e}")
            return {}

    def fetch_contributors(self, owner: str, repo: str) -> list:
        """Fetch repository contributors.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            List of contributors
        """
        cache_key = f"github_contributors_{owner}_{repo}"

        cached = self.cache.load(cache_key)
        if cached:
            return cached

        try:
            response = requests.get(
                f"{self.GITHUB_API}/repos/{owner}/{repo}/contributors",
                headers=self.headers,
                params={"per_page": 100},
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            self.cache.save(cache_key, data)

            return data
        except Exception:
            return []

    def fetch_commits(self, owner: str, repo: str, days: int = 30) -> list:
        """Fetch recent commits.

        Args:
            owner: Repository owner
            repo: Repository name
            days: Number of days to look back

        Returns:
            List of commits
        """
        cache_key = f"github_commits_{owner}_{repo}_{days}"

        cached = self.cache.load(cache_key)
        if cached:
            return cached

        since = (datetime.now() - timedelta(days=days)).isoformat()

        try:
            response = requests.get(
                f"{self.GITHUB_API}/repos/{owner}/{repo}/commits",
                headers=self.headers,
                params={"since": since, "per_page": 100},
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            self.cache.save(cache_key, data)

            return data
        except Exception:
            return []

    def fetch_issues(self, owner: str, repo: str, state: str = "open") -> list:
        """Fetch repository issues.

        Args:
            owner: Repository owner
            repo: Repository name
            state: Issue state (open/closed/all)

        Returns:
            List of issues
        """
        cache_key = f"github_issues_{owner}_{repo}_{state}"

        cached = self.cache.load(cache_key)
        if cached:
            return cached

        try:
            response = requests.get(
                f"{self.GITHUB_API}/repos/{owner}/{repo}/issues",
                headers=self.headers,
                params={"state": state, "per_page": 100},
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            self.cache.save(cache_key, data)

            return data
        except Exception:
            return []

    def fetch_pull_requests(self, owner: str, repo: str, state: str = "open") -> list:
        """Fetch repository pull requests.

        Args:
            owner: Repository owner
            repo: Repository name
            state: PR state (open/closed/all)

        Returns:
            List of PRs
        """
        cache_key = f"github_prs_{owner}_{repo}_{state}"

        cached = self.cache.load(cache_key)
        if cached:
            return cached

        try:
            response = requests.get(
                f"{self.GITHUB_API}/repos/{owner}/{repo}/pulls",
                headers=self.headers,
                params={"state": state, "per_page": 100},
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            self.cache.save(cache_key, data)

            return data
        except Exception:
            return []

    def score_activity(self, commit_count: int, contributor_count: int) -> int:
        """Score GitHub activity.

        Scoring rules:
        - Very active: >100 commits/month, >50 contributors -> 5
        - Active: >50 commits/month, >20 contributors -> 4
        - Moderate: >20 commits/month, >10 contributors -> 3
        - Low: >5 commits/month, >5 contributors -> 2
        - Inactive: <=5 commits/month -> 1

        Args:
            commit_count: Commit count in last 30 days
            contributor_count: Total contributor count

        Returns:
            Score (1-5)
        """
        if commit_count > 100 and contributor_count > 50:
            return 5
        elif commit_count > 50 and contributor_count > 20:
            return 4
        elif commit_count > 20 and contributor_count > 10:
            return 3
        elif commit_count > 5 and contributor_count > 5:
            return 2
        else:
            return 1

    def analyze(self, coin_name: str, repo_path: str) -> GithubData:
        """Perform full GitHub analysis.

        Args:
            coin_name: Coin name
            repo_path: Repository path (owner/repo)

        Returns:
            GithubData instance
        """
        # Parse repo path
        parts = repo_path.split("/")
        if len(parts) != 2:
            return GithubData(
                repo_url=f"https://github.com/{repo_path}",
                commit_count_30d=0,
                contributor_count=0,
                issue_count=0,
                pr_count=0,
                last_commit_date=datetime.now(),
                activity_score=1
            )

        owner, repo = parts

        # Fetch data
        repo_info = self.fetch_repo_info(owner, repo)
        contributors = self.fetch_contributors(owner, repo)
        commits = self.fetch_commits(owner, repo, days=30)
        issues = self.fetch_issues(owner, repo, state="open")
        prs = self.fetch_pull_requests(owner, repo, state="open")

        # Extract metrics
        commit_count = len(commits)
        contributor_count = len(contributors)
        issue_count = len(issues)
        pr_count = len(prs)

        # Get last commit date
        last_commit_date = datetime.now()
        if commits and len(commits) > 0:
            try:
                last_commit_date = datetime.strptime(
                    commits[0]["commit"]["author"]["date"],
                    "%Y-%m-%dT%H:%M:%SZ"
                )
            except (KeyError, ValueError):
                pass

        # Score activity
        activity_score = self.score_activity(commit_count, contributor_count)

        return GithubData(
            repo_url=f"https://github.com/{owner}/{repo}",
            commit_count_30d=commit_count,
            contributor_count=contributor_count,
            issue_count=issue_count,
            pr_count=pr_count,
            last_commit_date=last_commit_date,
            activity_score=activity_score
        )
