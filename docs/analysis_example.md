# 快速上手指南：Bitcoin 分析示例

本文档以 Bitcoin 为例，展示从数据采集到报告生成的完整流程。

---

## 1. 环境准备

```bash
pip install -r requirements.txt
cp config/settings.example.yaml config/settings.yaml
```

---

## 2. 数据采集

```bash
# 采集所有数据源
python scripts/data_collection/daily_collector.py

# 检查状态
python scripts/check_collection_status.py

# 设置定时任务
bash scripts/setup_cron.sh
```

---

## 3. 生成报告

```bash
# 单币种报告
python scripts/report/generate_report.py --coin bitcoin

# 多币种对比
python scripts/report/generate_report.py --top-n 20
```

---

## 4. 因子可视化

```bash
python scripts/analysis/visualize_factors.py --days 30
```

---

## 5. 回测分析

```bash
python scripts/analysis/backtest_simple.py --days 30 --freq weekly
```

---

## 6. 参数优化

```bash
python scripts/analysis/optimize_strategy.py --mock
```

---

## 7. 监控告警

```bash
# 终端检查
python scripts/check_collection_status.py --alerts

# 配置 webhook（编辑 settings.yaml）
python scripts/check_collection_status.py --alerts --notify
```

---

## 目录结构

```
claude_trade/
├── data/raw/         # 原始数据
├── data/factors/     # 因子计算结果
├── reports/          # 分析报告
├── scripts/          # 脚本
└── config/           # 配置
```

---

*最后更新: 2026-06-10*