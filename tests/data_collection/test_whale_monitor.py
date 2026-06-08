"""
鲸鱼监控模块测试

测试REST API轮询和阈值过滤逻辑（按native币数量）
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import json

from src.collector.whale_monitor import (
    WhaleTransaction,
    BTCWhaleMonitor,
    ETHWhaleMonitor,
    WebSocketWhaleMonitor,
    WhaleMonitorManager,
    DEFAULT_BTC_THRESHOLD,
    DEFAULT_ETH_THRESHOLD
)


class TestWhaleTransaction:
    """测试WhaleTransaction数据类"""

    def test_creation(self):
        """测试创建交易对象"""
        tx = WhaleTransaction(
            timestamp="2024-01-01T00:00:00",
            chain="BTC",
            tx_hash="abc123",
            amount_usd=500000.0,
            amount_native=10.5,
            from_address="addr1",
            to_address="addr2",
            tx_type="transfer"
        )
        assert tx.chain == "BTC"
        assert tx.amount_usd == 500000.0

    def test_to_csv_row(self):
        """测试CSV行转换"""
        tx = WhaleTransaction(
            timestamp="2024-01-01T00:00:00",
            chain="ETH",
            tx_hash="0xabc",
            amount_usd=1000000.0,
            amount_native=300.0,
            from_address="0xfrom",
            to_address="0xto",
            tx_type="transfer"
        )
        row = tx.to_csv_row()
        assert len(row) == 8
        assert row[0] == "2024-01-01T00:00:00"
        assert row[1] == "ETH"
        assert row[2] == "0xabc"


class TestBTCWhaleMonitor:
    """测试BTC鲸鱼监控器"""

    def test_init(self):
        """测试初始化"""
        monitor = BTCWhaleMonitor(threshold_btc=50, btc_price=100000)
        assert monitor.threshold_native == 50
        assert monitor.btc_price == 100000
        assert monitor.chain == "BTC"

    def test_default_threshold(self):
        """测试默认阈值"""
        monitor = BTCWhaleMonitor(btc_price=100000)
        assert monitor.threshold_native == DEFAULT_BTC_THRESHOLD  # 100 BTC

    @patch("src.collector.whale_monitor.requests.get")
    def test_fetch_transactions_empty(self, mock_get):
        """测试空交易响应"""
        mock_response = Mock()
        mock_response.json.return_value = {"txs": []}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        monitor = BTCWhaleMonitor(btc_price=100000)
        transactions = monitor.fetch_transactions()

        assert len(transactions) == 0

    @patch("src.collector.whale_monitor.requests.get")
    def test_fetch_transactions_with_data(self, mock_get):
        """测试获取BTC交易数据"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "txs": [
                {
                    "hash": "tx001",
                    "inputs": [{"prev_out": {"addr": "sender1"}}],
                    "out": [
                        {"value": 5000000000, "addr": "receiver1"},  # 50 BTC
                        {"value": 5000000000, "addr": "receiver2"}   # 50 BTC
                    ]
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        monitor = BTCWhaleMonitor(btc_price=100000)
        transactions = monitor.fetch_transactions()

        assert len(transactions) == 1
        assert transactions[0].tx_hash == "tx001"
        assert transactions[0].chain == "BTC"
        # 100 BTC total output
        assert transactions[0].amount_native == 100.0
        assert transactions[0].amount_usd == 10000000.0  # 100 * 100000

    def test_filter_large_transactions(self):
        """测试大额交易过滤（按BTC数量）"""
        monitor = BTCWhaleMonitor(threshold_btc=100, btc_price=50000)

        transactions = [
            WhaleTransaction("t1", "BTC", "h1", 200000, 150.0, "a", "b", "transfer"),  # 150 BTC
            WhaleTransaction("t2", "BTC", "h2", 50000, 50.0, "a", "b", "transfer"),   # 50 BTC
            WhaleTransaction("t3", "BTC", "h3", 100000, 100.0, "a", "b", "transfer"),  # 100 BTC
        ]

        large = monitor.filter_large_transactions(transactions)
        assert len(large) == 2  # 150 BTC and 100 BTC
        assert all(tx.amount_native >= 100 for tx in large)

    def test_websocket_fallback_log(self):
        """测试WebSocket降级日志"""
        monitor = BTCWhaleMonitor(btc_price=100000)
        # 当前WebSocket未实现，应该标记为使用REST
        assert monitor.use_websocket == False


class TestETHWhaleMonitor:
    """测试ETH鲸鱼监控器"""

    def test_init(self):
        """测试初始化"""
        monitor = ETHWhaleMonitor(
            api_key="test_key",
            threshold_eth=500,
            eth_price=4000,
            watch_addresses=["0xabc"]
        )
        assert monitor.api_key == "test_key"
        assert monitor.eth_price == 4000
        assert monitor.threshold_native == 500
        assert monitor.chain == "ETH"
        assert len(monitor.watch_addresses) == 1

    def test_default_threshold(self):
        """测试默认阈值"""
        monitor = ETHWhaleMonitor(api_key="test", eth_price=4000)
        assert monitor.threshold_native == DEFAULT_ETH_THRESHOLD  # 1000 ETH

    @patch("src.collector.whale_monitor.requests.get")
    @patch("src.collector.whale_monitor.time.sleep")
    def test_fetch_transactions(self, mock_sleep, mock_get):
        """测试获取ETH交易"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "1",
            "message": "OK",
            "result": [
                {
                    "hash": "0xtx001",
                    "from": "0xsender",
                    "to": "0xreceiver",
                    "value": str(50 * 10**18),  # 50 ETH
                    "timeStamp": "1704067200"  # 2024-01-01
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        monitor = ETHWhaleMonitor(
            api_key="test",
            eth_price=4000,
            watch_addresses=["0xwatch"]
        )
        transactions = monitor.fetch_transactions()

        assert len(transactions) == 1
        assert transactions[0].tx_hash == "0xtx001"
        assert transactions[0].chain == "ETH"
        assert transactions[0].amount_native == 50.0
        assert transactions[0].amount_usd == 200000.0  # 50 * 4000

    @patch("src.collector.whale_monitor.requests.get")
    @patch("src.collector.whale_monitor.time.sleep")
    def test_api_error_handling(self, mock_sleep, mock_get):
        """测试API错误处理"""
        mock_get.side_effect = Exception("Network error")

        monitor = ETHWhaleMonitor(
            api_key="test",
            eth_price=4000,
            watch_addresses=["0xabc"]
        )
        transactions = monitor.fetch_transactions()

        assert len(transactions) == 0  # 应该优雅地处理错误

    def test_filter_large_transactions(self):
        """测试大额交易过滤（按ETH数量）"""
        monitor = ETHWhaleMonitor(api_key="test", threshold_eth=1000, eth_price=4000)

        transactions = [
            WhaleTransaction("t1", "ETH", "h1", 5000000, 1500.0, "a", "b", "transfer"),  # 1500 ETH
            WhaleTransaction("t2", "ETH", "h2", 200000, 500.0, "a", "b", "transfer"),     # 500 ETH
            WhaleTransaction("t3", "ETH", "h3", 4000000, 1000.0, "a", "b", "transfer"),   # 1000 ETH
        ]

        large = monitor.filter_large_transactions(transactions)
        assert len(large) == 2  # 1500 ETH and 1000 ETH
        assert all(tx.amount_native >= 1000 for tx in large)


class TestWebSocketWhaleMonitor:
    """测试WebSocket鲸鱼监控器（占位符）"""

    def test_init(self):
        """测试初始化"""
        monitor = WebSocketWhaleMonitor(threshold_native=100)
        assert monitor.threshold_native == 100

    def test_fetch_transactions_returns_empty(self):
        """测试返回空列表（占位符）"""
        monitor = WebSocketWhaleMonitor()
        transactions = monitor.fetch_transactions()
        assert len(transactions) == 0

    def test_connect_not_implemented(self):
        """测试连接方法未实现"""
        monitor = WebSocketWhaleMonitor()
        with pytest.raises(NotImplementedError):
            monitor.connect()

    def test_subscribe_not_implemented(self):
        """测试订阅方法未实现"""
        monitor = WebSocketWhaleMonitor()
        with pytest.raises(NotImplementedError):
            monitor.subscribe(["0xabc"])


class TestWhaleMonitorManager:
    """测试监控管理器"""

    @patch("src.collector.whale_monitor.requests.get")
    def test_load_config_missing_file(self, mock_get):
        """测试加载不存在的配置文件"""
        manager = WhaleMonitorManager(config_path="nonexistent.yaml")
        assert manager.config == {}
        assert len(manager.monitors) == 0  # 没有启用的监控器

    def test_setup_with_config(self, tmp_path):
        """测试使用配置文件设置监控器"""
        config_content = """
whale_monitor:
  threshold_btc: 50
  threshold_eth: 500
  check_interval: 300
  btc:
    enabled: true
    price_usd: 100000
  eth:
    enabled: false
"""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(config_content)

        manager = WhaleMonitorManager(config_path=str(config_file))
        assert manager.config["whale_monitor"]["threshold_btc"] == 50
        assert manager.threshold_btc == 50
        assert manager.check_interval == 300
        # 应该有1个BTC监控器
        assert len(manager.monitors) == 1
        assert isinstance(manager.monitors[0], BTCWhaleMonitor)

    def test_threshold_override(self, tmp_path):
        """测试命令行参数覆盖配置文件"""
        config_content = """
whale_monitor:
  threshold_btc: 50
  threshold_eth: 500
  btc:
    enabled: true
    price_usd: 100000
  eth:
    enabled: false
"""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(config_content)

        # 命令行参数应该覆盖配置文件
        manager = WhaleMonitorManager(
            config_path=str(config_file),
            threshold_btc=200,  # 覆盖配置文件的50
            threshold_eth=2000
        )
        assert manager.threshold_btc == 200
        assert manager.threshold_eth == 2000

    @patch("src.collector.whale_monitor.requests.get")
    def test_collect_all(self, mock_get, tmp_path):
        """测试收集所有交易"""
        # Mock BTC API
        mock_btc_response = Mock()
        mock_btc_response.json.return_value = {"txs": []}
        mock_btc_response.raise_for_status = Mock()

        mock_get.return_value = mock_btc_response

        config_content = """
whale_monitor:
  threshold_btc: 100
  btc:
    enabled: true
    price_usd: 100000
  eth:
    enabled: false
"""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(config_content)

        manager = WhaleMonitorManager(config_path=str(config_file))
        transactions = manager.collect_all()

        assert isinstance(transactions, list)

    def test_save_to_csv(self, tmp_path):
        """测试保存CSV"""
        manager = WhaleMonitorManager.__new__(WhaleMonitorManager)
        manager.config = {}
        manager.output_dir = str(tmp_path)

        transactions = [
            WhaleTransaction("2024-01-01T00:00:00", "BTC", "hash1", 1000000.0, 10.0, "addr1", "addr2", "transfer"),
            WhaleTransaction("2024-01-01T00:01:00", "ETH", "hash2", 500000.0, 100.0, "addr3", "addr4", "transfer"),
        ]

        output_path = str(tmp_path / "test_output.csv")
        manager.save_to_csv(transactions, output_path)

        # 验证文件内容
        with open(output_path, "r") as f:
            content = f.read()
            assert "timestamp,chain,tx_hash" in content
            assert "BTC" in content
            assert "ETH" in content
            assert "hash1" in content
            assert "hash2" in content


class TestIntegration:
    """集成测试"""

    @patch("src.collector.whale_monitor.requests.get")
    def test_full_workflow(self, mock_get, tmp_path):
        """测试完整工作流程"""
        # Mock BTC API响应
        mock_btc_response = Mock()
        mock_btc_response.json.return_value = {
            "txs": [
                {
                    "hash": "big_whale_tx",
                    "inputs": [{"prev_out": {"addr": "whale_sender"}}],
                    "out": [
                        {"value": 2000000000, "addr": "whale_receiver"},  # 20 BTC
                    ]
                },
                {
                    "hash": "small_tx",
                    "inputs": [{"prev_out": {"addr": "small_sender"}}],
                    "out": [
                        {"value": 100000000, "addr": "small_receiver"},  # 1 BTC
                    ]
                }
            ]
        }
        mock_btc_response.raise_for_status = Mock()

        # Mock price API
        mock_price_response = Mock()
        mock_price_response.json.return_value = {
            "bitcoin": {"usd": 100000}
        }
        mock_price_response.raise_for_status = Mock()

        def mock_get_side_effect(url, timeout=None):
            if "unconfirmed" in url:
                return mock_btc_response
            elif "coingecko" in url:
                return mock_price_response
            return Mock()

        mock_get.side_effect = mock_get_side_effect

        # 创建配置 - 使用native币阈值
        config_content = """
whale_monitor:
  threshold_btc: 10  # 10 BTC阈值
  btc:
    enabled: true
    price_usd: 100000
  eth:
    enabled: false
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        # 运行监控
        manager = WhaleMonitorManager(config_path=str(config_file))
        transactions = manager.collect_all()

        # 只有一笔交易超过阈值 (20 BTC >= 10 BTC阈值)
        assert len(transactions) == 1
        assert transactions[0].tx_hash == "big_whale_tx"
        assert transactions[0].amount_native == 20.0
        assert transactions[0].amount_usd == 2000000.0

        # 保存CSV
        output_path = str(tmp_path / "whales.csv")
        manager.save_to_csv(transactions, output_path)

        with open(output_path, "r") as f:
            content = f.read()
            assert "big_whale_tx" in content

    @patch("src.collector.whale_monitor.requests.get")
    @patch("src.collector.whale_monitor.time.sleep")
    def test_monitoring_loop(self, mock_sleep, mock_get, tmp_path):
        """测试轮询监控循环"""
        # Mock API响应
        mock_response = Mock()
        mock_response.json.return_value = {"txs": []}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        config_content = """
whale_monitor:
  threshold_btc: 100
  check_interval: 5
  btc:
    enabled: true
    price_usd: 100000
  eth:
    enabled: false
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        manager = WhaleMonitorManager(
            config_path=str(config_file),
            output_dir=str(tmp_path)
        )

        # 验证配置加载正确
        assert manager.check_interval == 5
        assert manager.threshold_btc == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
