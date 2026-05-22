"""Analysis modules for cryptocurrency evaluation."""
from src.analysis.technical import TechnicalAnalyzer
from src.analysis.btc_dominance import BTCDominanceAnalyzer
from src.analysis.sentiment import SentimentAnalyzer
from src.analysis.onchain import OnchainAnalyzer
from src.analysis.github_analyzer import GithubAnalyzer

__all__ = [
    "TechnicalAnalyzer",
    "BTCDominanceAnalyzer",
    "SentimentAnalyzer",
    "OnchainAnalyzer",
    "GithubAnalyzer"
]