#!/usr/bin/env python3
"""
鲸鱼交易监控脚本

命令行运行鲸鱼监控，收集大额链上交易
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.collector.whale_monitor import WhaleMonitorManager, DEFAULT_OUTPUT_DIR


def main():
    """主函数"""
    import argparse
    import logging

    parser = argparse.ArgumentParser(
        description="鲸鱼交易监控 - 监控大额BTC/ETH链上交易"
    )
    parser.add_argument(
        "--config",
        default="config/settings.yaml",
        help="配置文件路径"
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help="输出目录（默认: data/raw/whale_alerts）"
    )
    parser.add_argument(
        "--threshold-btc",
        type=float,
        default=100,
        help="BTC大额交易阈值（BTC数量，默认100 BTC）"
    )
    parser.add_argument(
        "--threshold-eth",
        type=float,
        default=1000,
        help="ETH大额交易阈值（ETH数量，默认1000 ETH）"
    )
    parser.add_argument(
        "--check-interval",
        type=int,
        default=600,
        help="轮询检查间隔（秒，默认600秒即10分钟）"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=None,
        help="运行时长（秒），设置后将持续轮询监控"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="显示详细日志"
    )

    args = parser.parse_args()

    # 设置日志
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    print("鲸鱼交易监控器启动...")
    print(f"配置文件: {args.config}")
    print(f"输出目录: {args.output_dir}")
    print(f"BTC阈值: ≥{args.threshold_btc} BTC")
    print(f"ETH阈值: ≥{args.threshold_eth} ETH")
    print(f"轮询间隔: {args.check_interval}秒")
    if args.duration:
        print(f"运行时长: {args.duration}秒")

    # 运行监控
    try:
        manager = WhaleMonitorManager(
            config_path=args.config,
            threshold_btc=args.threshold_btc,
            threshold_eth=args.threshold_eth,
            check_interval=args.check_interval,
            output_dir=args.output_dir
        )

        if args.duration:
            # 持续监控模式
            manager.run_monitoring_loop(duration=args.duration)
        else:
            # 单次运行模式
            transactions = manager.collect_all()

            if transactions:
                output_path = manager._get_output_path()
                manager.save_to_csv(transactions, output_path)
                print(f"\n发现 {len(transactions)} 笔大额交易")
                print(f"已保存到: {output_path}")

                # 显示简要摘要
                btc_count = sum(1 for tx in transactions if tx.chain == "BTC")
                eth_count = sum(1 for tx in transactions if tx.chain == "ETH")
                total_usd = sum(tx.amount_usd for tx in transactions)

                print(f"\n摘要:")
                print(f"  BTC: {btc_count} 笔")
                print(f"  ETH: {eth_count} 笔")
                print(f"  总金额: ${total_usd:,.2f}")
            else:
                print("\n未发现大额交易")

    except Exception as e:
        logging.error(f"监控失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()