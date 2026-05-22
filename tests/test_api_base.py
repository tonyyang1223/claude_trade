"""Tests for API base class."""
import pytest
from abc import ABC
from src.api.base import BaseAPIClient


class TestBaseAPIClient:
    """Tests for BaseAPIClient class."""

    def test_is_abstract(self):
        """Test that BaseAPIClient is abstract."""
        assert issubclass(BaseAPIClient, ABC)
        with pytest.raises(TypeError):
            BaseAPIClient()

    def test_subclass_must_implement_methods(self):
        """Test subclasses must implement required methods."""
        class IncompleteClient(BaseAPIClient):
            pass

        with pytest.raises(TypeError):
            IncompleteClient()

    def test_complete_subclass_can_instantiate(self):
        """Test complete subclass can be instantiated."""
        class CompleteClient(BaseAPIClient):
            def get_coin_data(self, coin_id: str):
                return {"id": coin_id}

            def get_market_data(self):
                return {"total_market_cap": 1000000000000}

            def get_top_coins(self, limit: int = 100):
                return []

        client = CompleteClient()
        assert client is not None
        assert client.get_coin_data("bitcoin") == {"id": "bitcoin"}