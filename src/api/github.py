"""Enhanced GitHub API Client with comprehensive activity metrics.

Extends basic GitHub analysis with:
    - commit_velocity: Commits per day trend
    - contributor_growth: Contributor count change
    - issue_activity: Issue open/close rate
    - release_frequency: Release cadence
    - developer_activity_factor: Combined activity score
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import requests

from src.data.cache import DataCache


class GithubClient:
    """Enhanced GitHub API client for developer activity tracking.

    Features:
        - Rate limiting aware (5000 calls/hour with token)
        - Intelligent caching (6 hour TTL)
        - Comprehensive metrics extraction
        - Activity trend analysis

    Example:
        >>> client = GithubClient()
        >>> activity = client.get_developer_activity("bitcoin", "bitcoin/bitcoin")
        >>> print(activity["commit_velocity"])
    """

    GITHUB_API = "https://api.github.com"

    def __init__(
        self,
        cache_dir: Path = Path("data/cache"),
        api_token: Optional[str] = None
    ):
        """Initialize GitHub client.

        Args:
            cache_dir: Directory for caching data
            api_token: Optional GitHub API token for higher rate limits
        """
        self.cache = DataCache(cache_dir, expire_hours=6)
        self.api_token = api_token
        self.headers = {"Accept": "application/vnd.github.v3+json"}

        import os
        self.api_token = api_token or os.getenv("GITHUB_TOKEN")
        if self.api_token:
            self.headers["Authorization"] = f"token {self.api_token}"

    def _fetch_with_cache(
        self,
        url: str,
        cache_key: str,
        params: Dict = None,
        timeout: int = 30
    ) -> Any:
        """Fetch with caching support."""
        cached = self.cache.load(cache_key)
        if cached:
            return cached

        try:
            response = requests.get(
                url,
                headers=self.headers,
                params=params,
                timeout=timeout
            )
            response.raise_for_status()
            data = response.json()
            self.cache.save(cache_key, data)
            return data
        except requests.exceptions.RequestException as e:
            print(f"Warning: GitHub API request failed: {e}")
            return None

    def get_repo_info(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get repository basic information."""
        cache_key = f"github_repo_{owner}_{repo}"
        url = f"{self.GITHUB_API}/repos/{owner}/{repo}"
        return self._fetch_with_cache(url, cache_key) or {}

    def get_commits(
        self,
        owner: str,
        repo: str,
        since: datetime = None,
        until: datetime = None,
        per_page: int = 100
    ) -> List[Dict]:
        """Get repository commits."""
        cache_key = f"github_commits_{owner}_{repo}_{since}_{until}"
        url = f"{self.GITHUB_API}/repos/{owner}/{repo}/commits"

        params = {"per_page": per_page}
        if since:
            params["since"] = since.isoformat()
        if until:
            params["until"] = until.isoformat()

        return self._fetch_with_cache(url, cache_key, params) or []

    def get_contributors(self, owner: str, repo: str, per_page: int = 100) -> List[Dict]:
        """Get repository contributors."""
        cache_key = f"github_contributors_{owner}_{repo}"
        url = f"{self.GITHUB_API}/repos/{owner}/{repo}/contributors"
        return self._fetch_with_cache(url, cache_key, {"per_page": per_page}) or []

    def get_issues(
        self,
        owner: str,
        repo: str,
        state: str = "all",
        since: datetime = None,
        per_page: int = 100
    ) -> List[Dict]:
        """Get repository issues."""
        cache_key = f"github_issues_{owner}_{repo}_{state}_{since}"
        url = f"{self.GITHUB_API}/repos/{owner}/{repo}/issues"

        params = {"state": state, "per_page": per_page}
        if since:
            params["since"] = since.isoformat()

        return self._fetch_with_cache(url, cache_key, params) or []

    def get_releases(self, owner: str, repo: str, per_page: int = 30) -> List[Dict]:
        """Get repository releases."""
        cache_key = f"github_releases_{owner}_{repo}"
        url = f"{self.GITHUB_API}/repos/{owner}/{repo}/releases"
        return self._fetch_with_cache(url, cache_key, {"per_page": per_page}) or []

    def get_stats_commit_activity(self, owner: str, repo: str) -> List[Dict]:
        """Get commit activity stats (last year, weekly breakdown)."""
        cache_key = f"github_stats_commits_{owner}_{repo}"
        url = f"{self.GITHUB_API}/repos/{owner}/{repo}/stats/commit_activity"
        return self._fetch_with_cache(url, cache_key) or []

    def get_stats_contributors(self, owner: str, repo: str) -> List[Dict]:
        """Get contributor stats."""
        cache_key = f"github_stats_contributors_{owner}_{repo}"
        url = f"{self.GITHUB_API}/repos/{owner}/{repo}/stats/contributors"
        return self._fetch_with_cache(url, cache_key) or []

    def calculate_commit_velocity(self, owner: str, repo: str, days: int = 30) -> Dict[str, float]:
        """Calculate commit velocity metrics."""
        now = datetime.now()
        period_start = now - timedelta(days=days)
        prev_start = period_start - timedelta(days=days)

        current_commits = self.get_commits(owner, repo, since=period_start)
        current_count = len(current_commits) if current_commits else 0

        prev_commits = self.get_commits(owner, repo, since=prev_start, until=period_start)
        prev_count = len(prev_commits) if prev_commits else 0

        commits_per_day = current_count / days if days > 0 else 0

        if prev_count > 0:
            velocity_change = ((current_count - prev_count) / prev_count) * 100
        else:
            velocity_change = 0.0

        if velocity_change > 10:
            trend = "up"
        elif velocity_change < -10:
            trend = "down"
        else:
            trend = "stable"

        return {
            "commits_per_day": round(commits_per_day, 2),
            "velocity_change": round(velocity_change, 2),
            "trend": trend,
            "current_period_commits": current_count,
            "previous_period_commits": prev_count
        }

    def calculate_contributor_growth(self, owner: str, repo: str) -> Dict[str, Any]:
        """Calculate contributor growth metrics."""
        contributors = self.get_contributors(owner, repo)
        total_contributors = len(contributors) if contributors else 0

        stats = self.get_stats_contributors(owner, repo)

        active_contributors = 0
        if stats:
            for contributor_stat in stats:
                weeks = contributor_stat.get("weeks", [])
                for week in weeks[-5:]:
                    if week.get("c", 0) > 0:
                        active_contributors += 1
                        break

        growth_rate = 0.0
        if stats and len(stats) >= 10:
            recent_weeks = []
            prev_weeks = []
            for stat in stats[:10]:
                weeks = stat.get("weeks", [])
                recent = sum(1 for w in weeks[-12:] if w.get("c", 0) > 0)
                prev = sum(1 for w in weeks[-24:-12] if w.get("c", 0) > 0)
                recent_weeks.append(recent)
                prev_weeks.append(prev)

            recent_active = len([r for r in recent_weeks if r > 0])
            prev_active = len([p for p in prev_weeks if p > 0])

            if prev_active > 0:
                growth_rate = ((recent_active - prev_active) / prev_active) * 100

        return {
            "total_contributors": total_contributors,
            "active_contributors": active_contributors,
            "growth_rate": round(growth_rate, 2)
        }

    def calculate_issue_activity(self, owner: str, repo: str, days: int = 30) -> Dict[str, Any]:
        """Calculate issue activity metrics."""
        since = datetime.now() - timedelta(days=days)

        open_issues = self.get_issues(owner, repo, state="open")
        open_count = len([i for i in open_issues if "pull_request" not in i]) if open_issues else 0

        closed_issues = self.get_issues(owner, repo, state="closed", since=since)
        closed_count = len([i for i in closed_issues if "pull_request" not in i]) if closed_issues else 0

        resolution_times = []
        if closed_issues:
            for issue in closed_issues[:50]:
                if "pull_request" not in issue:
                    try:
                        created = datetime.strptime(issue["created_at"], "%Y-%m-%dT%H:%M:%SZ")
                        closed = datetime.strptime(issue["closed_at"], "%Y-%m-%dT%H:%M:%SZ")
                        resolution_times.append((closed - created).days)
                    except (KeyError, ValueError):
                        continue

        avg_resolution = sum(resolution_times) / len(resolution_times) if resolution_times else 0
        issue_velocity = closed_count / days if days > 0 else 0

        return {
            "open_issues": open_count,
            "closed_issues": closed_count,
            "avg_resolution_days": round(avg_resolution, 1),
            "issue_velocity": round(issue_velocity, 2)
        }

    def calculate_release_frequency(self, owner: str, repo: str, days: int = 365) -> Dict[str, Any]:
        """Calculate release frequency metrics."""
        releases = self.get_releases(owner, repo)
        since = datetime.now() - timedelta(days=days)

        if not releases:
            return {
                "total_releases": 0,
                "releases_per_month": 0,
                "last_release": None,
                "days_since_release": -1
            }

        recent_releases = []
        for release in releases:
            try:
                published = datetime.strptime(release["published_at"], "%Y-%m-%dT%H:%M:%SZ")
                if published > since:
                    recent_releases.append(published)
            except (KeyError, ValueError):
                continue

        total_releases = len(recent_releases)
        releases_per_month = (total_releases / days) * 30

        last_release = max(recent_releases) if recent_releases else None
        days_since = (datetime.now() - last_release).days if last_release else -1

        return {
            "total_releases": total_releases,
            "releases_per_month": round(releases_per_month, 2),
            "last_release": last_release.isoformat() if last_release else None,
            "days_since_release": days_since
        }

    def get_developer_activity(self, coin_name: str, repo_path: str) -> Dict[str, Any]:
        """Get comprehensive developer activity metrics."""
        parts = repo_path.split("/")
        if len(parts) != 2:
            return self._empty_activity(coin_name)

        owner, repo = parts

        repo_info = self.get_repo_info(owner, repo)

        commit_velocity = self.calculate_commit_velocity(owner, repo)
        contributor_growth = self.calculate_contributor_growth(owner, repo)
        issue_activity = self.calculate_issue_activity(owner, repo)
        release_frequency = self.calculate_release_frequency(owner, repo)

        activity_score = self._calculate_activity_score(
            commit_velocity, contributor_growth, issue_activity, release_frequency
        )

        confidence = 0.95 if repo_info else 0.5

        return {
            "coin_name": coin_name,
            "repo_path": repo_path,
            "stars": repo_info.get("stargazers_count", 0),
            "forks": repo_info.get("forks_count", 0),
            "watchers": repo_info.get("watchers_count", 0),
            "commit_velocity": commit_velocity,
            "contributor_growth": contributor_growth,
            "issue_activity": issue_activity,
            "release_frequency": release_frequency,
            "developer_activity_score": activity_score,
            "confidence": confidence,
            "source": "GitHub API",
            "timestamp": datetime.now().isoformat()
        }

    def _calculate_activity_score(
        self,
        commit_velocity: Dict,
        contributor_growth: Dict,
        issue_activity: Dict,
        release_frequency: Dict
    ) -> int:
        """Calculate combined developer activity score (1-5)."""
        commits_per_day = commit_velocity.get("commits_per_day", 0)
        velocity_score = min(100, commits_per_day * 5)

        active = contributor_growth.get("active_contributors", 0)
        total = contributor_growth.get("total_contributors", 1)
        contributor_score = min(100, (active / total * 100) if total > 0 else 0)

        closed = issue_activity.get("closed_issues", 0)
        open_i = issue_activity.get("open_issues", 1)
        resolution = issue_activity.get("avg_resolution_days", 999)

        issue_score = 50
        if closed > open_i * 0.5:
            issue_score += 25
        if resolution < 30:
            issue_score += 25
        issue_score = min(100, issue_score)

        releases_per_month = release_frequency.get("releases_per_month", 0)
        days_since = release_frequency.get("days_since_release", 999)

        release_score = min(100, releases_per_month * 20)
        if days_since >= 0 and days_since < 30:
            release_score = min(100, release_score + 20)

        combined = (
            velocity_score * 0.30 +
            contributor_score * 0.25 +
            issue_score * 0.25 +
            release_score * 0.20
        )

        if combined >= 80:
            return 5
        elif combined >= 60:
            return 4
        elif combined >= 40:
            return 3
        elif combined >= 20:
            return 2
        else:
            return 1

    def _empty_activity(self, coin_name: str) -> Dict[str, Any]:
        """Return empty activity data."""
        return {
            "coin_name": coin_name,
            "repo_path": None,
            "stars": 0,
            "forks": 0,
            "watchers": 0,
            "commit_velocity": {},
            "contributor_growth": {},
            "issue_activity": {},
            "release_frequency": {},
            "developer_activity_score": 1,
            "confidence": 0.1,
            "source": "Fallback",
            "timestamp": datetime.now().isoformat()
        }