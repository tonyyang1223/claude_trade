# 数据采集监控告警功能实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `scripts/check_collection_status.py` 增加终端红色告警和 Webhook 通知功能

**Architecture:** 在现有检查脚本中新增通知模块，通过 YAML 配置文件读取 webhook 设置，使用 requests 库发送 HTTP 通知

**Tech Stack:** Python 3.9+, requests, PyYAML, pytest

---

## 文件结构

| 文件 | 职责 |
|------|------|
| `scripts/check_collection_status.py` | 主脚本，包含检查逻辑和新增的通知功能 |
| `config/settings.example.yaml` | 配置模板，新增 alert 配置示例 |
| `tests/test_check_collection_status.py` | 单元测试文件（新建） |

---

## Task 1: 更新配置示例文件

**Files:**
- Modify: `config/settings.example.yaml:30-33`

- [ ] **Step 1: 在 notification 部分添加 alert 配置**

修改 `config/settings.example.yaml`，在 `notification:` 部分添加：

```yaml
notification:
  # Alert settings (optional)
  telegram_bot_token: ""
  telegram_chat_id: ""

  # Data collection alert webhook
  alert:
    webhook_url: ""  # Slack or Telegram webhook URL
    webhook_type: "slack"  # Options: slack, telegram (default: slack)
```

- [ ] **Step 2: 验证 YAML 格式正确**

Run: `python -c "import yaml; yaml.safe_load(open('config/settings.example.yaml'))"`
Expected: No error

- [ ] **Step 3: Commit**

```bash
git add config/settings.example.yaml
git commit -m "config: add alert webhook settings"
```

---

## Task 2: 添加配置加载函数

**Files:**
- Modify: `scripts/check_collection_status.py:1-25`

- [ ] **Step 1: 添加 imports**

在 `scripts/check_collection_status.py` 文件顶部的 import 区域添加：

```python
import yaml
import requests
```

- [ ] **Step 2: 添加 AlertConfig 数据类**

在 `CollectionStatusChecker` 类之前添加：

```python
@dataclass
class AlertConfig:
    """Alert configuration from settings.yaml"""
    webhook_url: str = ""
    webhook_type: str = "slack"  # slack or telegram
```

- [ ] **Step 3: 添加 _load_alert_config 方法**

在 `CollectionStatusChecker` 类中添加方法：

```python
def _load_alert_config(self) -> AlertConfig:
    """Load alert configuration from settings.yaml"""
    settings_path = self.project_dir / "config" / "settings.yaml"
    
    if not settings_path.exists():
        return AlertConfig()
    
    try:
        with open(settings_path, 'r') as f:
            settings = yaml.safe_load(f) or {}
        
        alert = settings.get('notification', {}).get('alert', {})
        return AlertConfig(
            webhook_url=alert.get('webhook_url', ''),
            webhook_type=alert.get('webhook_type', 'slack')
        )
    except Exception:
        return AlertConfig()
```

- [ ] **Step 4: 在 __init__ 中初始化 alert_config**

修改 `__init__` 方法：

```python
def __init__(self):
    self.project_dir = project_root
    self.log_dir = self.project_dir / "logs"
    self.data_dir = self.project_dir / "data" / "raw"
    self.alert_config = self._load_alert_config()
    self.results = {}
```

- [ ] **Step 5: Commit**

```bash
git add scripts/check_collection_status.py
git commit -m "feat(alert): add config loading for webhook settings"
```

---

## Task 3: 添加 Webhook 通知函数

**Files:**
- Modify: `scripts/check_collection_status.py`

- [ ] **Step 1: 添加 _send_webhook 方法**

在 `CollectionStatusChecker` 类中添加：

```python
def _send_webhook(self, status: str, missing_sources: List[str], timestamp: str) -> bool:
    """Send webhook notification.
    
    Args:
        status: 'healthy' or 'unhealthy'
        missing_sources: List of missing/stale data sources
        timestamp: ISO 8601 timestamp
    
    Returns:
        True if sent successfully, False otherwise
    """
    if not self.alert_config.webhook_url:
        print("Warning: No webhook_url configured, skipping notification")
        return False
    
    try:
        if self.alert_config.webhook_type == "telegram":
            payload = self._build_telegram_payload(status, missing_sources, timestamp)
        else:
            payload = self._build_slack_payload(status, missing_sources, timestamp)
        
        response = requests.post(
            self.alert_config.webhook_url,
            json=payload,
            timeout=5
        )
        
        if response.status_code == 200:
            return True
        else:
            print(f"Warning: Webhook returned status {response.status_code}")
            return False
    
    except requests.Timeout:
        print("Warning: Webhook request timed out")
        return False
    except Exception as e:
        print(f"Warning: Webhook failed: {e}")
        return False
```

- [ ] **Step 2: 添加 _build_slack_payload 方法**

```python
def _build_slack_payload(self, status: str, missing_sources: List[str], timestamp: str) -> dict:
    """Build Slack webhook payload."""
    if status == "healthy":
        return {
            "text": "📊 Data Collection Status: healthy",
            "attachments": [{
                "color": "good",
                "fields": [
                    {"title": "Status", "value": "✅ All data sources healthy", "short": True},
                    {"title": "Timestamp", "value": timestamp, "short": True}
                ]
            }]
        }
    else:
        missing_str = ", ".join(missing_sources) if missing_sources else "None"
        return {
            "text": "📊 Data Collection Status: unhealthy",
            "attachments": [{
                "color": "danger",
                "fields": [
                    {"title": "Status", "value": "unhealthy", "short": True},
                    {"title": "Missing Sources", "value": missing_str, "short": True},
                    {"title": "Timestamp", "value": timestamp, "short": True}
                ]
            }]
        }
```

- [ ] **Step 3: 添加 _build_telegram_payload 方法**

```python
def _build_telegram_payload(self, status: str, missing_sources: List[str], timestamp: str) -> dict:
    """Build Telegram webhook payload."""
    if status == "healthy":
        text = f"📊 *Data Collection Status: healthy*\n\n✅ All data sources healthy\n🕐 {timestamp}"
    else:
        missing_str = ", ".join(f"`{s}`" for s in missing_sources) if missing_sources else "None"
        text = f"📊 *Data Collection Status: unhealthy*\n\n⚠️ Missing: {missing_str}\n🕐 {timestamp}"
    
    return {
        "text": text,
        "parse_mode": "Markdown"
    }
```

- [ ] **Step 4: Commit**

```bash
git add scripts/check_collection_status.py
git commit -m "feat(alert): add webhook notification methods"
```

---

## Task 4: 更新 JSON 输出格式

**Files:**
- Modify: `scripts/check_collection_status.py:37-64`

- [ ] **Step 1: 添加 _get_missing_sources 方法**

在 `CollectionStatusChecker` 类中添加：

```python
def _get_missing_sources(self) -> List[str]:
    """Get list of missing/stale data sources."""
    missing = []
    freshness = self.results['checks'].get('data_freshness', {})
    
    for source, details in freshness.get('sources', {}).items():
        if not details.get('healthy', True):
            missing.append(source)
    
    return missing
```

- [ ] **Step 2: 修改 check_all 方法，添加 status 和 missing_sources**

修改 `check_all` 方法的返回部分：

```python
def check_all(self) -> Dict[str, Any]:
    """Run all status checks."""
    self.results = {
        'timestamp': datetime.now().isoformat(),
        'checks': {}
    }

    # 1. Check crontab
    self.results['checks']['crontab'] = self._check_crontab()

    # 2. Check last run time
    self.results['checks']['last_run'] = self._check_last_run()

    # 3. Check data freshness
    self.results['checks']['data_freshness'] = self._check_data_freshness()

    # 4. Check error count
    self.results['checks']['errors'] = self._check_errors()

    # 5. Check data integrity
    self.results['checks']['integrity'] = self._check_data_integrity()

    # Calculate overall health
    is_healthy = all(
        c.get('healthy', True) for c in self.results['checks'].values()
    )
    
    # Add status and missing_sources
    self.results['status'] = "healthy" if is_healthy else "unhealthy"
    self.results['missing_sources'] = self._get_missing_sources()
    self.results['healthy'] = is_healthy

    return self.results
```

- [ ] **Step 3: Commit**

```bash
git add scripts/check_collection_status.py
git commit -m "feat(alert): add status and missing_sources to JSON output"
```

---

## Task 5: 添加终端告警输出

**Files:**
- Modify: `scripts/check_collection_status.py`

- [ ] **Step 1: 添加 ANSI 颜色常量**

在文件顶部常量区域添加：

```python
# ANSI color codes
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RESET = '\033[0m'
```

- [ ] **Step 2: 添加 print_alert 方法**

在 `CollectionStatusChecker` 类中添加：

```python
def print_alert(self, use_color: bool = True):
    """Print alert message for missing sources."""
    status = self.results.get('status', 'unknown')
    missing = self.results.get('missing_sources', [])
    timestamp = self.results.get('timestamp', '')
    
    if status == "healthy":
        if use_color:
            print(f"{GREEN}✅ All data sources healthy{RESET}")
        else:
            print("✅ All data sources healthy")
        return
    
    # Unhealthy status
    if use_color:
        print(f"{RED}❌ DATA COLLECTION ALERT - {timestamp}{RESET}\n")
        print(f"{YELLOW}⚠️ Missing/Stale Data Sources:{RESET}")
    else:
        print(f"❌ DATA COLLECTION ALERT - {timestamp}\n")
        print("⚠️ Missing/Stale Data Sources:")
    
    freshness = self.results['checks'].get('data_freshness', {})
    for source in missing:
        details = freshness.get('sources', {}).get(source, {})
        reason = details.get('message', 'Unknown issue')
        age = details.get('age_hours')
        
        if age:
            reason = f"Stale data (last: {age}h ago)"
        
        print(f"  • {source} - {reason}")
    
    print("\nRun: python scripts/data_collection/daily_collector.py")
```

- [ ] **Step 3: Commit**

```bash
git add scripts/check_collection_status.py
git commit -m "feat(alert): add terminal alert output with color"
```

---

## Task 6: 更新命令行参数和 main 函数

**Files:**
- Modify: `scripts/check_collection_status.py:326-356`

- [ ] **Step 1: 添加新命令行参数**

修改 `main()` 函数中的 argparse 部分：

```python
def main():
    parser = argparse.ArgumentParser(description="Check data collection status")

    parser.add_argument('--alerts', '-a', action='store_true', help="Only show alerts")
    parser.add_argument('--json', '-j', action='store_true', help="Output as JSON")
    parser.add_argument('--notify', action='store_true', help="Send webhook notification")
    parser.add_argument('--no-color', action='store_true', help="Disable colored output")

    args = parser.parse_args()

    checker = CollectionStatusChecker()
    results = checker.check_all()

    if args.alerts:
        use_color = not args.no_color
        checker.print_alert(use_color=use_color)
        
        if args.notify:
            checker._send_webhook(
                status=results['status'],
                missing_sources=results['missing_sources'],
                timestamp=results['timestamp']
            )
        
        sys.exit(0 if results['healthy'] else 1)

    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        checker.print_report()

    sys.exit(0 if results['healthy'] else 1)
```

- [ ] **Step 2: Commit**

```bash
git add scripts/check_collection_status.py
git commit -m "feat(alert): add --notify and --no-color CLI arguments"
```

---

## Task 7: 添加单元测试

**Files:**
- Create: `tests/test_check_collection_status.py`

- [ ] **Step 1: 创建测试文件**

创建 `tests/test_check_collection_status.py`：

```python
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
```

- [ ] **Step 2: 运行测试验证**

Run: `pytest tests/test_check_collection_status.py -v`
Expected: All tests pass

- [ ] **Step 3: Commit**

```bash
git add tests/test_check_collection_status.py
git commit -m "test: add unit tests for alert features"
```

---

## Task 8: 集成测试

**Files:**
- None (manual testing)

- [ ] **Step 1: 测试 JSON 输出格式**

Run: `python scripts/check_collection_status.py --json | python -c "import json,sys; d=json.load(sys.stdin); print('status:', d.get('status')); print('missing_sources:', d.get('missing_sources'))"`
Expected: Output shows status and missing_sources fields

- [ ] **Step 2: 测试告警输出**

Run: `python scripts/check_collection_status.py --alerts`
Expected: Shows alert message or "✅ All data sources healthy"

- [ ] **Step 3: 测试无颜色模式**

Run: `python scripts/check_collection_status.py --alerts --no-color`
Expected: Output without ANSI color codes

- [ ] **Step 4: 运行完整测试套件**

Run: `pytest tests/ -v --tb=short`
Expected: All tests pass

---

## Self-Review Checklist

| 检查项 | 状态 |
|--------|------|
| Spec 覆盖 | ✅ 所有设计要求都有对应任务 |
| Placeholder 扫描 | ✅ 无 TBD/TODO |
| 类型一致性 | ✅ 函数签名和类型一致 |
| 测试覆盖 | ✅ 所有新增功能有测试 |

---

## 执行选择

计划完成并保存到 `docs/superpowers/plans/2026-06-08-data-collection-alerting-plan.md`

**两种执行方式：**

1. **Subagent-Driven (推荐)** - 为每个任务派发新的 subagent，任务间审查，快速迭代

2. **Inline Execution** - 在当前会话中使用 executing-plans 批量执行，带检查点

**您选择哪种方式？**
