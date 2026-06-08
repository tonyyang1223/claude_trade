# 数据采集监控告警功能设计

> **创建日期**: 2026-06-08
> **状态**: 待审核

---

## 1. 概述

### 1.1 目标

为 `scripts/check_collection_status.py` 增加告警功能，确保数据采集问题能被及时发现。

### 1.2 背景

当前数据积累阶段仅 4 天，任何一天的采集失败都会损失宝贵样本。现有的检查脚本只输出状态报告，缺少主动告警能力。

### 1.3 范围

- 终端红色告警输出
- Webhook 通知（Slack / Telegram）
- JSON 输出格式优化

---

## 2. 详细设计

### 2.1 JSON 输出格式

**新增字段**：

```json
{
  "status": "healthy",
  "missing_sources": [],
  "timestamp": "2026-06-08T10:00:00",
  "checks": {
    "crontab": {...},
    "data_freshness": {...},
    "errors": {...},
    "integrity": {...},
    "last_run": {...}
  }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `status` | `"healthy"` / `"unhealthy"` | 总体健康状态 |
| `missing_sources` | `string[]` | 缺失/过期的数据源列表 |
| `timestamp` | string (ISO 8601) | 检查时间 |

### 2.2 配置文件

在 `config/settings.yaml` 中新增：

```yaml
alert:
  webhook_url: "https://hooks.slack.com/services/xxx"
  webhook_type: "slack"  # 可选值: slack, telegram，默认 slack
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `alert.webhook_url` | 是 | Webhook URL |
| `alert.webhook_type` | 否 | 默认 `slack`，支持 `slack` / `telegram` |

### 2.3 终端告警输出

**触发条件**: `--alerts` 模式或有异常时

**输出示例**：

```
❌ DATA COLLECTION ALERT - 2026-06-08 10:00:00

⚠️ Missing/Stale Data Sources:
  • coingecko - No data (last: 48h ago)
  • defillama - Stale data (last: 30h ago)

Run: python scripts/data_collection/daily_collector.py
```

**实现**：
- 使用 `\033[91m` ANSI 红色码
- 支持 `--no-color` 参数禁用颜色

### 2.4 Webhook 通知格式

**通知策略**: 每次运行都发送通知

**Slack 格式**：

```json
{
  "text": "📊 Data Collection Status: unhealthy",
  "attachments": [{
    "color": "danger",
    "fields": [
      {"title": "Status", "value": "unhealthy", "short": true},
      {"title": "Missing Sources", "value": "coingecko, defillama", "short": true},
      {"title": "Timestamp", "value": "2026-06-08 10:00:00", "short": true}
    ]
  }]
}
```

**Telegram 格式**：

```json
{
  "text": "📊 *Data Collection Status: unhealthy*\n\n⚠️ Missing: `coingecko`, `defillama`\n🕐 2026-06-08 10:00:00",
  "parse_mode": "Markdown"
}
```

**健康状态**：
- Slack: `"color": "good"`, text 显示 "✅ All data sources healthy"
- Telegram: 显示 "✅ All data sources healthy"

### 2.5 命令行参数

| 参数 | 说明 |
|------|------|
| `--json` | 输出 JSON 格式（已有，调整输出结构） |
| `--alerts` | 仅显示告警（已有） |
| `--notify` | 发送 Webhook 通知 |
| `--no-color` | 禁用终端颜色输出 |

**使用示例**：

```bash
# 检查并显示报告
python scripts/check_collection_status.py

# 输出 JSON（监控系统用）
python scripts/check_collection_status.py --json

# 仅显示告警 + 发送通知（适合 crontab）
python scripts/check_collection_status.py --alerts --notify

# 禁用颜色（日志文件用）
python scripts/check_collection_status.py --no-color
```

### 2.6 错误处理

| 场景 | 处理方式 |
|------|----------|
| `settings.yaml` 不存在 | 跳过通知，打印警告 |
| `webhook_url` 未配置 | 跳过通知，打印警告 |
| Webhook 请求失败 | 打印错误日志，不中断程序 |
| 网络超时 | 5 秒超时，重试 1 次 |

---

## 3. 实现方案

**方案**: 直接在 `scripts/check_collection_status.py` 中增强（方案 A）

**理由**:
- 通知逻辑不超过 50 行，无需分离模块
- 与现有代码风格一致
- 遵循 YAGNI 原则

**改动文件**:
- `scripts/check_collection_status.py` - 主要改动
- `config/settings.example.yaml` - 添加 alert 配置示例

---

## 4. 测试计划

| 测试场景 | 验证点 |
|----------|--------|
| `--json` 输出 | 包含 `status` 和 `missing_sources` 字段 |
| 健康状态 | 终端无红色告警，webhook 发送成功消息 |
| 缺失数据源 | 终端显示红色告警，webhook 发送异常消息 |
| `--notify` 无配置 | 打印警告，不中断程序 |
| Webhook 失败 | 打印错误，不中断程序 |
| `--no-color` | 输出无 ANSI 颜色码 |

---

## 5. 风险与约束

| 风险 | 缓解措施 |
|------|----------|
| Webhook 请求阻塞 | 设置 5 秒超时 |
| 配置文件格式错误 | 捕获异常，跳过通知 |

---

## 6. 后续扩展

- 邮件通知（如需要）
- 告警静默期（避免频繁通知）
- 多 webhook 支持
