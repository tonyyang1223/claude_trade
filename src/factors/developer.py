"""Developer activity factors: GitHub metrics."""
from src.factors import register_factor, FactorCategory, FactorSource
from src.factors.registry import registry
from src.api.github import GithubClient


@register_factor(
    name="github_commit_velocity",
    display_name="GitHub Commit Velocity",
    category=FactorCategory.DEVELOPER,
    source=FactorSource.GITHUB,
    description="Average commits per day in last 30 days",
    confidence=0.90,
    version="1.0.0",
    tags=["developer", "github", "velocity"],
    higher_is_better=True,
    typical_range=(0, 20)
)
def compute_github_commit_velocity(repo_path: str) -> float:
    client = GithubClient()
    parts = repo_path.split("/")
    if len(parts) != 2:
        return 0.0
    velocity = client.calculate_commit_velocity(parts[0], parts[1])
    return float(velocity.get("commits_per_day", 0))


@register_factor(
    name="github_contributor_growth",
    display_name="GitHub Contributor Growth",
    category=FactorCategory.DEVELOPER,
    source=FactorSource.GITHUB,
    description="Active contributor growth rate (%)",
    confidence=0.85,
    version="1.0.0",
    tags=["developer", "github", "contributors"],
    higher_is_better=True,
    typical_range=(-50, 100)
)
def compute_github_contributor_growth(repo_path: str) -> float:
    client = GithubClient()
    parts = repo_path.split("/")
    if len(parts) != 2:
        return 0.0
    growth = client.calculate_contributor_growth(parts[0], parts[1])
    return float(growth.get("growth_rate", 0))


@register_factor(
    name="github_issue_activity",
    display_name="GitHub Issue Activity",
    category=FactorCategory.DEVELOPER,
    source=FactorSource.GITHUB,
    description="Issues closed per day in last 30 days",
    confidence=0.80,
    version="1.0.0",
    tags=["developer", "github", "issues"],
    higher_is_better=True,
    typical_range=(0, 5)
)
def compute_github_issue_activity(repo_path: str) -> float:
    client = GithubClient()
    parts = repo_path.split("/")
    if len(parts) != 2:
        return 0.0
    activity = client.calculate_issue_activity(parts[0], parts[1])
    return float(activity.get("issue_velocity", 0))


@register_factor(
    name="github_release_frequency",
    display_name="GitHub Release Frequency",
    category=FactorCategory.DEVELOPER,
    source=FactorSource.GITHUB,
    description="Releases per month",
    confidence=0.85,
    version="1.0.0",
    tags=["developer", "github", "releases"],
    higher_is_better=True,
    typical_range=(0, 4)
)
def compute_github_release_frequency(repo_path: str) -> float:
    client = GithubClient()
    parts = repo_path.split("/")
    if len(parts) != 2:
        return 0.0
    releases = client.calculate_release_frequency(parts[0], parts[1])
    return float(releases.get("releases_per_month", 0))


@register_factor(
    name="developer_activity_score",
    display_name="Developer Activity Score",
    category=FactorCategory.DEVELOPER,
    source=FactorSource.GITHUB,
    description="Combined developer activity score (1-5)",
    confidence=0.90,
    version="1.0.0",
    tags=["developer", "github", "composite"],
    higher_is_better=True,
    typical_range=(1, 5)
)
def compute_developer_activity_score(coin_name: str, repo_path: str) -> float:
    client = GithubClient()
    activity = client.get_developer_activity(coin_name, repo_path)
    return float(activity.get("developer_activity_score", 1))


@registry.register_normalizer("github_commit_velocity")
def normalize_commit_velocity(raw_value: float) -> float:
    normalized = min(1.0, raw_value / 20)
    return max(0.0, normalized)


@registry.register_normalizer("github_contributor_growth")
def normalize_contributor_growth(raw_value: float) -> float:
    clamped = max(-50, min(100, raw_value))
    normalized = 0.5 + (clamped / 200)
    return max(0.0, min(1.0, normalized))


@registry.register_normalizer("github_issue_activity")
def normalize_issue_activity(raw_value: float) -> float:
    normalized = min(1.0, raw_value / 5)
    return max(0.0, normalized)


@registry.register_normalizer("github_release_frequency")
def normalize_release_frequency(raw_value: float) -> float:
    normalized = min(1.0, raw_value / 4)
    return max(0.0, normalized)


@registry.register_normalizer("developer_activity_score")
def normalize_developer_score(raw_value: float) -> float:
    normalized = (raw_value - 1) / 4
    return max(0.0, min(1.0, normalized))
