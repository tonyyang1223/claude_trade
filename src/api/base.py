"""Base class for API clients."""
from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseAPIClient(ABC):
    """Abstract base class for cryptocurrency API clients.

    All API clients must implement these methods to provide
    consistent interface for data collection.
    """

    @abstractmethod
    def get_coin_data(self, coin_id: str) -> Dict[str, Any]:
        """Get data for a single cryptocurrency.

        Args:
            coin_id: Unique identifier for the coin

        Returns:
            Dictionary containing coin data
        """
        pass

    @abstractmethod
    def get_market_data(self) -> Dict[str, Any]:
        """Get overall market data.

        Returns:
            Dictionary containing market-level data like
            total market cap, dominance, etc.
        """
        pass

    @abstractmethod
    def get_top_coins(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get top cryptocurrencies by market cap.

        Args:
            limit: Maximum number of coins to return

        Returns:
            List of coin data dictionaries
        """
        pass