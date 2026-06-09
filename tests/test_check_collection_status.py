"""Tests for check_collection_status.py alert features."""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys

# Add project root
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.check_collection_status import CollectionStatusChecker, AlertConfig


class TestAlertConfig:
    """Test AlertConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = AlertConfig()
        assert config.webhook_url == ""
        assert config.webhook_type == "slack"

    def test_custom_values(self):
        """Test custom configuration values."""
        config = AlertConfig(
            webhook_url="https://hooks.slack.com/services/xxx",
            webhook_type="telegram"
        )
        assert config.webhook_url == "https://hooks.slack.com/services/xxx"
        assert config.webhook_type == "telegram"


class TestMissingSources:
    """Test missing sources detection."""

    def test_no_missing_sources(self):
        """Test when all sources are healthy."""
        checker = CollectionStatusChecker()
        checker.results = {
            'checks': {
                'data_freshness': {
                    'sources': {
                        'coingecko': {'healthy': True},
                        'defillama': {'healthy': True}
                    }
                }
            }
        }

        missing = checker._get_missing_sources()
        assert missing == []

    def test_one_missing_source(self):
        """Test when one source is missing."""
        checker = CollectionStatusChecker()
        checker.results = {
            'checks': {
                'data_freshness': {
                    'sources': {
                        'coingecko': {'healthy': True},
                        'defillama': {'healthy': False}
                    }
                }
            }
        }

        missing = checker._get_missing_sources()
        assert missing == ['defillama']

    def test_multiple_missing_sources(self):
        """Test when multiple sources are missing."""
        checker = CollectionStatusChecker()
        checker.results = {
            'checks': {
                'data_freshness': {
                    'sources': {
                        'coingecko': {'healthy': False},
                        'defillama': {'healthy': False},
                        'github': {'healthy': True}
                    }
                }
            }
        }

        missing = checker._get_missing_sources()
        assert set(missing) == {'coingecko', 'defillama'}


class TestWebhookPayload:
    """Test webhook payload building."""

    def test_slack_payload_healthy(self):
        """Test Slack payload for healthy status."""
        checker = CollectionStatusChecker()
        payload = checker._build_slack_payload(
            status="healthy",
            missing_sources=[],
            timestamp="2026-06-08T10:00:00"
        )

        assert payload['text'] == "📊 Data Collection Status: healthy"
        assert payload['attachments'][0]['color'] == "good"

    def test_slack_payload_unhealthy(self):
        """Test Slack payload for unhealthy status."""
        checker = CollectionStatusChecker()
        payload = checker._build_slack_payload(
            status="unhealthy",
            missing_sources=["coingecko", "defillama"],
            timestamp="2026-06-08T10:00:00"
        )

        assert payload['text'] == "📊 Data Collection Status: unhealthy"
        assert payload['attachments'][0]['color'] == "danger"
        assert "coingecko" in payload['attachments'][0]['fields'][1]['value']

    def test_telegram_payload_healthy(self):
        """Test Telegram payload for healthy status."""
        checker = CollectionStatusChecker()
        payload = checker._build_telegram_payload(
            status="healthy",
            missing_sources=[],
            timestamp="2026-06-08T10:00:00"
        )

        assert "healthy" in payload['text']
        assert payload['parse_mode'] == "Markdown"

    def test_telegram_payload_unhealthy(self):
        """Test Telegram payload for unhealthy status."""
        checker = CollectionStatusChecker()
        payload = checker._build_telegram_payload(
            status="unhealthy",
            missing_sources=["coingecko"],
            timestamp="2026-06-08T10:00:00"
        )

        assert "unhealthy" in payload['text']
        assert "`coingecko`" in payload['text']


class TestWebhookSend:
    """Test webhook sending."""

    @patch('scripts.check_collection_status.requests.post')
    def test_send_webhook_success(self, mock_post):
        """Test successful webhook send."""
        mock_post.return_value = MagicMock(status_code=200)

        checker = CollectionStatusChecker()
        checker.alert_config = AlertConfig(
            webhook_url="https://hooks.slack.com/services/xxx"
        )

        result = checker._send_webhook(
            status="healthy",
            missing_sources=[],
            timestamp="2026-06-08T10:00:00"
        )

        assert result is True
        mock_post.assert_called_once()

    @patch('scripts.check_collection_status.requests.post')
    def test_send_webhook_no_url(self, mock_post):
        """Test webhook send without URL configured."""
        checker = CollectionStatusChecker()
        checker.alert_config = AlertConfig(webhook_url="")

        result = checker._send_webhook(
            status="healthy",
            missing_sources=[],
            timestamp="2026-06-08T10:00:00"
        )

        assert result is False
        mock_post.assert_not_called()

    @patch('scripts.check_collection_status.requests.post')
    def test_send_webhook_timeout(self, mock_post):
        """Test webhook send with timeout."""
        import requests
        mock_post.side_effect = requests.Timeout()

        checker = CollectionStatusChecker()
        checker.alert_config = AlertConfig(
            webhook_url="https://hooks.slack.com/services/xxx"
        )

        result = checker._send_webhook(
            status="healthy",
            missing_sources=[],
            timestamp="2026-06-08T10:00:00"
        )

        assert result is False


class TestJsonOutput:
    """Test JSON output format."""

    def test_json_output_has_status(self):
        """Test that JSON output includes status field."""
        checker = CollectionStatusChecker()

        # Mock the check methods
        with patch.object(checker, '_check_crontab', return_value={'healthy': True}):
            with patch.object(checker, '_check_last_run', return_value={'healthy': True}):
                with patch.object(checker, '_check_data_freshness', return_value={'healthy': True, 'sources': {}}):
                    with patch.object(checker, '_check_errors', return_value={'healthy': True}):
                        with patch.object(checker, '_check_data_integrity', return_value={'healthy': True, 'sources': {}}):
                            results = checker.check_all()

        assert 'status' in results
        assert 'missing_sources' in results
        assert results['status'] in ['healthy', 'unhealthy']
        assert isinstance(results['missing_sources'], list)
