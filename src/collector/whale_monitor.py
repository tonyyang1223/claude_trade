"""
鲸鱼交易监控模块

监控大额链上交易（鲸鱼活动），支持BTC和ETH。
- BTC: 使用Blockchain.com REST API轮询未确认交易
- ETH: 使用Etherscan API监控预设地址的交易
- WebSocket接口优先尝试，失败时降级REST
"""

import csv
import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

import requests
import yaml

logger = logging.getLogger(__name__)

# 默认输出目录
DEFAULT_OUTPUT_DIR = "data/raw/whale_alerts"

# 默认阈值（native币数量）
DEFAULT_BTC_THRESHOLD = 100.0  # 100 BTC
DEFAULT_ETH_THRESHOLD = 1000.0  # 1000 ETH

# 默认轮询间隔
DEFAULT_CHECK_INTERVAL = 600  # 10分钟


@dataclass
class WhaleTransaction:
    """鲸鱼交易数据结构"""
    timestamp: str
    chain: str  # 'BTC' or 'ETH'
    tx_hash: str
    amount_usd: float
    amount_native: float
    from_address: str
    to_address: str
    tx_type: str  # 'transfer', 'unknown'

    def to_csv_row(self) -> List[str]:
        """转换为CSV行"""
        return [
            self.timestamp,
            self.chain,
            self.tx_hash,
            f"{self.amount_usd:.2f}",
            f"{self.amount_native:.8f}",
            self.from_address,
            self.to_address,
            self.tx_type
        ]


class BaseWhaleMonitor(ABC):
    """鲸鱼监控基类"""

    def __init__(
        self,
        threshold_native: float = 100.0,
        chain: str = "BTC"
    ):
        """
        初始化

        Args:
            threshold_native: 大额交易阈值（native币数量）
            chain: 链类型 ('BTC' or 'ETH')
        """
        self.threshold_native = threshold_native
        self.chain = chain
        self.use_websocket = False
        self.websocket_failed = False

    @abstractmethod
    def fetch_transactions(self) -> List[WhaleTransaction]:
        """获取交易数据"""
        pass

    def filter_large_transactions(self, transactions: List[WhaleTransaction]) -> List[WhaleTransaction]:
        """过滤出大额交易（按native币数量）"""
        large_txs = [tx for tx in transactions if tx.amount_native >= self.threshold_native]
        if large_txs:
            logger.info(f"发现 {len(large_txs)} 笔大额{self.chain}交易（≥{self.threshold_native} {self.chain}）")
        return large_txs

    def try_websocket_connection(self) -> bool:
        """
        尝试WebSocket连接（子类可覆盖实现）

        Returns:
            True if WebSocket connected successfully, False otherwise
        """
        return False

    def log_websocket_status(self) -> None:
        """记录WebSocket状态"""
        if self.use_websocket:
            logger.info(f"{self.chain}监控器使用WebSocket连接")
        else:
            logger.warning(f"{self.chain}监控器WebSocket连接失败，降级使用REST API")


class BTCWhaleMonitor(BaseWhaleMonitor):
    """
    BTC鲸鱼监控器

    使用Blockchain.com API轮询未确认交易池
    """

    API_URL = "https://blockchain.info/unconfirmed-transactions?format=json"

    def __init__(self, threshold_btc: float = DEFAULT_BTC_THRESHOLD, btc_price: float = 0.0):
        super().__init__(threshold_native=threshold_btc, chain="BTC")
        self.btc_price = btc_price
        self.use_websocket = False
        self._try_connect_websocket()

    def _try_connect_websocket(self) -> None:
        """尝试WebSocket连接，失败则降级REST"""
        # WebSocket连接尝试（预留实现）
        # 实际WebSocket endpoint: wss://ws.blockchain.info/inv
        try:
            # TODO: 实现真实WebSocket连接
            # 目前标记为不可用，使用REST API
            self.use_websocket = self.try_websocket_connection()
            self.log_websocket_status()
        except Exception as e:
            logger.warning(f"BTC WebSocket连接失败: {e}，将使用REST API")
            self.use_websocket = False
            self.websocket_failed = True

    def try_websocket_connection(self) -> bool:
        """
        尝试WebSocket连接

        Returns:
            False (当前未实现，总是返回False)
        """
        # 预留WebSocket连接逻辑
        # 实际实现需要使用websocket-client或websockets库
        logger.debug("BTC WebSocket连接暂未实现，使用REST API")
        return False

    def fetch_transactions(self) -> List[WhaleTransaction]:
        """
        获取BTC未确认交易

        Returns:
            交易列表
        """
        transactions = []

        try:
            logger.info(f"获取BTC未确认交易（阈值: ≥{self.threshold_native} BTC）")
            response = requests.get(self.API_URL, timeout=10)
            response.raise_for_status()
            data = response.json()

            txs = data.get("txs", [])
            logger.info(f"获取到 {len(txs)} 笔BTC未确认交易")

            for tx in txs:
                # 计算交易金额（输出总和）
                total_output = sum(
                    Decimal(str(out.get("value", 0))) / Decimal("100000000")
                    for out in tx.get("out", [])
                )

                if total_output <= 0:
                    continue

                # 获取地址
                inputs = tx.get("inputs", [])
                outputs = tx.get("out", [])

                from_addr = ""
                if inputs and len(inputs) > 0:
                    prev_out = inputs[0].get("prev_out", {})
                    from_addr = prev_out.get("addr", "")

                to_addr = ""
                if outputs and len(outputs) > 0:
                    to_addr = outputs[0].get("addr", "")

                # 计算美元价值
                amount_usd = float(total_output) * self.btc_price

                whale_tx = WhaleTransaction(
                    timestamp=datetime.utcnow().isoformat(),
                    chain="BTC",
                    tx_hash=tx.get("hash", ""),
                    amount_usd=amount_usd,
                    amount_native=float(total_output),
                    from_address=from_addr,
                    to_address=to_addr,
                    tx_type="transfer"
                )
                transactions.append(whale_tx)

        except requests.RequestException as e:
            logger.error(f"获取BTC交易失败: {e}")
        except Exception as e:
            logger.error(f"处理BTC交易数据失败: {e}")

        return transactions


class ETHWhaleMonitor(BaseWhaleMonitor):
    """
    ETH鲸鱼监控器

    使用Etherscan API监控预设地址的交易列表
    """

    API_URL = "https://api.etherscan.io/api"

    def __init__(
        self,
        api_key: str,
        threshold_eth: float = DEFAULT_ETH_THRESHOLD,
        eth_price: float = 0.0,
        watch_addresses: Optional[List[str]] = None
    ):
        super().__init__(threshold_native=threshold_eth, chain="ETH")
        self.api_key = api_key
        self.eth_price = eth_price
        self.watch_addresses = watch_addresses or []
        self.use_websocket = False
        self._try_connect_websocket()

    def _try_connect_websocket(self) -> None:
        """尝试WebSocket连接，失败则降级REST"""
        # WebSocket连接尝试（预留实现）
        try:
            self.use_websocket = self.try_websocket_connection()
            self.log_websocket_status()
        except Exception as e:
            logger.warning(f"ETH WebSocket连接失败: {e}，将使用REST API")
            self.use_websocket = False
            self.websocket_failed = True

    def try_websocket_connection(self) -> bool:
        """
        尝试WebSocket连接

        Returns:
            False (当前未实现，总是返回False)
        """
        # 预留WebSocket连接逻辑
        # 可使用 wss://etherscan.io/ws 或第三方服务
        logger.debug("ETH WebSocket连接暂未实现，使用REST API")
        return False

    def fetch_transactions(self) -> List[WhaleTransaction]:
        """
        获取ETH交易（监控预设地址）

        Returns:
            交易列表
        """
        transactions = []

        logger.info(f"获取ETH交易（阈值: ≥{self.threshold_native} ETH，监控 {len(self.watch_addresses)} 个地址）")

        for address in self.watch_addresses:
            try:
                txs = self._fetch_address_transactions(address)
                transactions.extend(txs)
                time.sleep(0.25)  # 避免API速率限制
            except Exception as e:
                logger.error(f"获取地址 {address} 交易失败: {e}")

        return transactions

    def _fetch_address_transactions(self, address: str) -> List[WhaleTransaction]:
        """获取单个地址的交易"""
        transactions = []

        try:
            params = {
                "module": "account",
                "action": "txlist",
                "address": address,
                "startblock": "0",
                "endblock": "99999999",
                "sort": "desc",
                "apikey": self.api_key
            }

            response = requests.get(self.API_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "1":
                logger.warning(f"Etherscan API返回错误: {data.get('message')}")
                return transactions

            txs = data.get("result", [])
            logger.info(f"地址 {address[:10]}... 获取到 {len(txs)} 笔交易")

            for tx in txs[:100]:  # 限制处理数量
                value_wei = int(tx.get("value", 0))
                value_eth = value_wei / 1e18

                if value_eth <= 0:
                    continue

                amount_usd = value_eth * self.eth_price

                whale_tx = WhaleTransaction(
                    timestamp=datetime.fromtimestamp(int(tx.get("timeStamp", 0))).isoformat(),
                    chain="ETH",
                    tx_hash=tx.get("hash", ""),
                    amount_usd=amount_usd,
                    amount_native=value_eth,
                    from_address=tx.get("from", ""),
                    to_address=tx.get("to", ""),
                    tx_type="transfer"
                )
                transactions.append(whale_tx)

        except requests.RequestException as e:
            logger.error(f"Etherscan API请求失败: {e}")
        except Exception as e:
            logger.error(f"处理ETH交易数据失败: {e}")

        return transactions


class WebSocketWhaleMonitor(BaseWhaleMonitor):
    """
    WebSocket鲸鱼监控器（占位符）

    后续可扩展支持实时WebSocket连接
    """

    def __init__(self, threshold_native: float = DEFAULT_BTC_THRESHOLD):
        super().__init__(threshold_native=threshold_native)
        logger.warning("WebSocket监控器尚未实现，返回空列表")

    def fetch_transactions(self) -> List[WhaleTransaction]:
        """获取交易（占位符）"""
        logger.debug("WebSocket监控器返回空交易列表（占位符）")
        return []

    def connect(self) -> None:
        """建立WebSocket连接（占位符）"""
        raise NotImplementedError("WebSocket连接功能尚未实现")

    def subscribe(self, addresses: List[str]) -> None:
        """订阅地址（占位符）"""
        raise NotImplementedError("地址订阅功能尚未实现")


class WhaleMonitorManager:
    """
    鲸鱼监控管理器

    统一管理多个链的监控器，提供CSV输出和轮询功能
    """

    def __init__(
        self,
        config_path: str = "config/settings.yaml",
        threshold_btc: float = DEFAULT_BTC_THRESHOLD,
        threshold_eth: float = DEFAULT_ETH_THRESHOLD,
        check_interval: int = DEFAULT_CHECK_INTERVAL,
        output_dir: str = DEFAULT_OUTPUT_DIR
    ):
        """
        初始化管理器

        Args:
            config_path: 配置文件路径
            threshold_btc: BTC大额交易阈值（BTC数量）
            threshold_eth: ETH大额交易阈值（ETH数量）
            check_interval: 轮询检查间隔（秒）
            output_dir: 输出目录
        """
        self.config = self._load_config(config_path)
        self.threshold_btc = threshold_btc
        self.threshold_eth = threshold_eth
        self.check_interval = check_interval
        self.output_dir = output_dir
        self.monitors: List[BaseWhaleMonitor] = []
        self._setup_monitors()

    def _load_config(self, config_path: str) -> dict:
        """加载配置文件"""
        # 尝试多个配置路径
        paths = [
            config_path,
            os.path.join(os.path.dirname(__file__), "..", "..", config_path),
            os.path.join(os.getcwd(), config_path)
        ]

        for path in paths:
            if os.path.exists(path):
                with open(path, "r") as f:
                    logger.info(f"加载配置文件: {path}")
                    return yaml.safe_load(f) or {}

        logger.warning(f"配置文件不存在: {config_path}，使用默认配置")
        return {}

    def _setup_monitors(self) -> None:
        """设置监控器"""
        whale_config = self.config.get("whale_monitor", {})

        # 从配置文件读取阈值（如果存在）
        config_threshold_btc = whale_config.get("threshold_btc", self.threshold_btc)
        config_threshold_eth = whale_config.get("threshold_eth", self.threshold_eth)
        config_check_interval = whale_config.get("check_interval", self.check_interval)

        # 使用传入参数优先（命令行参数）
        self.threshold_btc = self.threshold_btc if self.threshold_btc != DEFAULT_BTC_THRESHOLD else config_threshold_btc
        self.threshold_eth = self.threshold_eth if self.threshold_eth != DEFAULT_ETH_THRESHOLD else config_threshold_eth
        self.check_interval = self.check_interval if self.check_interval != DEFAULT_CHECK_INTERVAL else config_check_interval

        logger.info(f"监控配置: BTC阈值={self.threshold_btc} BTC, ETH阈值={self.threshold_eth} ETH, 轮询间隔={self.check_interval}秒")

        # BTC监控器
        btc_config = whale_config.get("btc", {})
        if btc_config.get("enabled", False):
            btc_price = btc_config.get("price_usd", 0)
            if btc_price == 0:
                btc_price = self._get_btc_price()

            monitor = BTCWhaleMonitor(
                threshold_btc=self.threshold_btc,
                btc_price=btc_price
            )
            self.monitors.append(monitor)
            logger.info(f"BTC监控器已启用，阈值: ≥{self.threshold_btc} BTC")

        # ETH监控器
        eth_config = whale_config.get("eth", {})
        if eth_config.get("enabled", False):
            api_key = os.environ.get("ETHERSCAN_API_KEY", eth_config.get("api_key", ""))
            if not api_key:
                logger.warning("ETHERSCAN_API_KEY未配置，ETH监控器禁用")
            else:
                eth_price = eth_config.get("price_usd", 0)
                if eth_price == 0:
                    eth_price = self._get_eth_price()

                watch_addresses = eth_config.get("watch_addresses", [])
                monitor = ETHWhaleMonitor(
                    api_key=api_key,
                    threshold_eth=self.threshold_eth,
                    eth_price=eth_price,
                    watch_addresses=watch_addresses
                )
                self.monitors.append(monitor)
                logger.info(f"ETH监控器已启用，监控 {len(watch_addresses)} 个地址，阈值: ≥{self.threshold_eth} ETH")

        # WebSocket监控器（预留）
        ws_config = whale_config.get("websocket", {})
        if ws_config.get("enabled", False):
            monitor = WebSocketWhaleMonitor(threshold_native=self.threshold_btc)
            self.monitors.append(monitor)
            logger.info("WebSocket监控器已启用（占位符）")

    def _get_btc_price(self) -> float:
        """获取BTC实时价格"""
        try:
            response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", timeout=5)
            data = response.json()
            return data.get("bitcoin", {}).get("usd", 0)
        except Exception as e:
            logger.warning(f"获取BTC价格失败: {e}")
            return 0

    def _get_eth_price(self) -> float:
        """获取ETH实时价格"""
        try:
            response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd", timeout=5)
            data = response.json()
            return data.get("ethereum", {}).get("usd", 0)
        except Exception as e:
            logger.warning(f"获取ETH价格失败: {e}")
            return 0

    def collect_all(self) -> List[WhaleTransaction]:
        """
        收集所有监控器的大额交易

        Returns:
            大额交易列表
        """
        all_transactions = []

        for monitor in self.monitors:
            try:
                transactions = monitor.fetch_transactions()
                large_txs = monitor.filter_large_transactions(transactions)
                all_transactions.extend(large_txs)
                logger.info(f"{monitor.__class__.__name__}: 发现 {len(large_txs)} 笔大额交易")
            except Exception as e:
                logger.error(f"{monitor.__class__.__name__} 收集失败: {e}")

        logger.info(f"总计收集 {len(all_transactions)} 笔大额交易")
        return all_transactions

    def run_monitoring_loop(self, duration: Optional[int] = None) -> None:
        """
        运行监控循环

        Args:
            duration: 运行时长（秒），None表示持续运行
        """
        logger.info(f"启动监控循环，轮询间隔: {self.check_interval}秒")
        start_time = time.time()
        iteration = 0

        while True:
            iteration += 1
            logger.info(f"=== 第 {iteration} 轮监控 ===")

            try:
                transactions = self.collect_all()
                if transactions:
                    output_path = self._get_output_path()
                    self.save_to_csv(transactions, output_path)
                    logger.info(f"已保存 {len(transactions)} 笔交易到 {output_path}")
            except Exception as e:
                logger.error(f"监控循环出错: {e}")

            # 检查是否超时
            if duration and (time.time() - start_time) >= duration:
                logger.info(f"监控完成，运行时长: {duration}秒")
                break

            # 等待下一轮
            logger.info(f"等待 {self.check_interval} 秒后进行下一轮监控...")
            time.sleep(self.check_interval)

    def _get_output_path(self) -> str:
        """生成输出文件路径"""
        date_str = datetime.now().strftime("%Y%m%d")
        filename = f"whale_alerts_{date_str}.csv"
        return os.path.join(self.output_dir, filename)

    def save_to_csv(self, transactions: List[WhaleTransaction], output_path: str) -> None:
        """
        保存交易到CSV文件

        Args:
            transactions: 交易列表
            output_path: 输出文件路径
        """
        # 确保目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            # 写入表头
            writer.writerow([
                "timestamp", "chain", "tx_hash", "amount_usd",
                "amount_native", "from_address", "to_address", "type"
            ])
            # 写入数据
            for tx in transactions:
                writer.writerow(tx.to_csv_row())

        logger.info(f"已保存 {len(transactions)} 笔交易到 {output_path}")


def main():
    """主函数 - 用于命令行运行"""
    import argparse

    parser = argparse.ArgumentParser(description="鲸鱼交易监控")
    parser.add_argument("--config", default="config/settings.yaml", help="配置文件路径")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_DIR, help="输出目录")
    parser.add_argument("--threshold-btc", type=float, default=DEFAULT_BTC_THRESHOLD, help="BTC大额交易阈值（BTC数量）")
    parser.add_argument("--threshold-eth", type=float, default=DEFAULT_ETH_THRESHOLD, help="ETH大额交易阈值（ETH数量）")
    parser.add_argument("--check-interval", type=int, default=DEFAULT_CHECK_INTERVAL, help="轮询检查间隔（秒）")
    parser.add_argument("--duration", type=int, default=None, help="运行时长（秒），None表示持续运行")
    parser.add_argument("--verbose", action="store_true", help="显示详细日志")

    args = parser.parse_args()

    # 设置日志
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    print("鲸鱼交易监控器启动...")
    print(f"配置文件: {args.config}")
    print(f"输出目录: {args.output}")
    print(f"BTC阈值: ≥{args.threshold_btc} BTC")
    print(f"ETH阈值: ≥{args.threshold_eth} ETH")
    print(f"轮询间隔: {args.check_interval}秒")

    # 运行监控
    try:
        manager = WhaleMonitorManager(
            config_path=args.config,
            threshold_btc=args.threshold_btc,
            threshold_eth=args.threshold_eth,
            check_interval=args.check_interval,
            output_dir=args.output
        )

        # 单次运行或持续运行
        if args.duration:
            manager.run_monitoring_loop(duration=args.duration)
        else:
            transactions = manager.collect_all()
            if transactions:
                output_path = manager._get_output_path()
                manager.save_to_csv(transactions, output_path)
                print(f"\n发现 {len(transactions)} 笔大额交易")
                print(f"已保存到: {output_path}")
            else:
                print("\n未发现大额交易")

    except Exception as e:
        logging.error(f"监控失败: {e}")
        raise


if __name__ == "__main__":
    main()
