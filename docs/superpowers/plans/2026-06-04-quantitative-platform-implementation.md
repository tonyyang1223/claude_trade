# 量化平台分阶段实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建完整的数字货币量化投研平台，包含数据采集、因子分析、回测框架和监控系统

**Architecture:** 模块化分层架构 - CLI脚本层 → 核心模块层（采集/分析/回测）→ 因子引擎层 → 数据存储层（Parquet）

**Tech Stack:** Python 3.9+, pandas, pyarrow, plotly, pytest, pytest-mock, websocket-client

---

## 前置依赖

**现有代码结构（需复用）：**
```
src/api/
├── coingecko.py      # CoinGecko API 客户端
├── coinglass.py      # CoinGlass API 客户端（资金费率/持仓量）
├── defillama.py      # DefiLlama API 客户端（TVL/稳定币）
├── github.py         # GitHub API 客户端
└── reddit.py         # Reddit API 客户端

src/analysis/
├── scorer.py         # 评分系统（7维度权重）
├── technical.py      # 技术分析
└── ...

tests/                # 现有测试目录
```

**关键修正点：**
1. ✅ 数据校验 - 必需字段检查、负值检查、时间戳验证
2. ✅ 测试隔离 - conftest.py 提供统一 Mock 数据生成器
3. ✅ 回测调整 - UTC 00:00 调仓、可配置频率（daily/weekly）、手续费模型
4. ✅ 代码复用 - 集成现有 5 个 API 客户端（src/api/）
5. ✅ 监控降级 - WebSocket 优先，REST 轮询备用
6. ✅ 因子衔接 - 检查数据新鲜度后再计算

---

## 阶段 1：数据采集自动化 + 单元测试（P0）

**预计时间：** Day 0-3
**依赖：** 无

### Task 1.1: 创建测试基础设施

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/data_collection/__init__.py`

- [ ] **Step 1: 创建 tests/data_collection/__init__.py**

```python
# tests/data_collection/__init__.py
"""Data collection tests package."""
```

- [ ] **Step 2: 创建 conftest.py - Mock 数据生成器**

```python
# tests/conftest.py
"""Shared pytest fixtures and mock data generators."""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List


@pytest.fixture
def mock_coingecko_response() -> Dict[str, Any]:
    """Generate mock CoinGecko API response."""
    return {
        'id': 'bitcoin',
        'symbol': 'btc',
        'name': 'Bitcoin',
        'current_price': 45000.00,
        'market_cap': 850000000000,
        'market_cap_rank': 1,
        'total_volume': 25000000000,
        'price_change_24h': 1200.50,
        'price_change_percentage_24h': 2.74,
        'circulating_supply': 18800000,
        'total_supply': 21000000,
        'ath': 69000.00,
        'atl': 67.81,
        'last_updated': datetime.now().isoformat()
    }


@pytest.fixture
def mock_coinglass_response() -> Dict[str, Any]:
    """Generate mock CoinGlass API response for funding rate."""
    return {
        'symbol': 'BTC',
        'fundingRate': 0.0001,
        'fundingTime': int(datetime.now().timestamp() * 1000),
        'exchange': 'binance'
    }


@pytest.fixture
def mock_defillama_response() -> Dict[str, Any]:
    """Generate mock DefiLlama API response for TVL."""
    return {
        'chain': 'Ethereum',
        'tvl': 50000000000,
        'chainId': 'ethereum',
        'name': 'Ethereum',
        'tokenSymbol': 'ETH'
    }


@pytest.fixture
def mock_github_response() -> Dict[str, Any]:
    """Generate mock GitHub API response."""
    return {
        'id': 123456,
        'name': 'bitcoin',
        'full_name': 'bitcoin/bitcoin',
        'stargazers_count': 70000,
        'forks_count': 35000,
        'open_issues_count': 500,
        'watchers_count': 3500,
        'pushed_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat()
    }


@pytest.fixture
def mock_reddit_response() -> Dict[str, Any]:
    """Generate mock Reddit API response."""
    return {
        'kind': 'listing',
        'data': {
            'children': [
                {
                    'data': {
                        'subreddit': 'bitcoin',
                        'title': 'Bitcoin price discussion',
                        'score': 500,
                        'num_comments': 150,
                        'created_utc': datetime.now().timestamp()
                    }
                }
                for _ in range(10)
            ]
        }
    }


@pytest.fixture
def sample_factor_data() -> pd.DataFrame:
    """Generate sample factor data with 16 factors for 30 days."""
    dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
    
    # 16 factors based on spec
    factors = {
        'funding_rate': np.random.uniform(-0.001, 0.001, 30),
        'open_interest': np.random.uniform(1e9, 5e9, 30),
        'tvl_change_7d': np.random.uniform(-10, 10, 30),
        'stablecoin_flow': np.random.uniform(-1e8, 1e8, 30),
        'github_commits': np.random.randint(10, 100, 30),
        'github_stars': np.random.randint(1000, 100000, 30),
        'reddit_mentions': np.random.randint(50, 500, 30),
        'reddit_sentiment': np.random.uniform(-1, 1, 30),
        'twitter_mentions': np.random.randint(100, 1000, 30),
        'price_momentum_7d': np.random.uniform(-15, 15, 30),
        'price_momentum_30d': np.random.uniform(-30, 30, 30),
        'volume_ratio': np.random.uniform(0.5, 2.0, 30),
        'btc_dominance_change': np.random.uniform(-2, 2, 30),
        'exchange_inflow': np.random.uniform(1000, 10000, 30),
        'exchange_outflow': np.random.uniform(1000, 10000, 30),
        'whale_activity': np.random.randint(0, 20, 30)
    }
    
    df = pd.DataFrame(factors, index=dates)
    df.index.name = 'date'
    return df


@pytest.fixture
def mock_all_api_responses(
    mock_coingecko_response,
    mock_coinglass_response,
    mock_defillama_response,
    mock_github_response,
    mock_reddit_response
) -> Dict[str, Dict[str, Any]]:
    """Combine all mock API responses."""
    return {
        'coingecko': mock_coingecko_response,
        'coinglass': mock_coinglass_response,
        'defillama': mock_defillama_response,
        'github': mock_github_response,
        'reddit': mock_reddit_response
    }


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create temporary data directory structure."""
    data_dir = tmp_path / "data"
    raw_dir = data_dir / "raw"
    processed_dir = data_dir / "processed"
    raw_dir.mkdir(parents=True)
    processed_dir.mkdir(parents=True)
    return data_dir


@pytest.fixture
def temp_config_file(tmp_path):
    """Create temporary config file."""
    config_content = """
data:
  raw_dir: data/raw
  processed_dir: data/processed
  
collection:
  retry_attempts: 3
  retry_delay: 1
  
whale_monitor:
  enabled: true
  thresholds:
    btc: 100
    eth: 1000
  check_interval: 600
"""
    config_file = tmp_path / "settings.yaml"
    config_file.write_text(config_content)
    return config_file
```

- [ ] **Step 3: 验证 conftest 创建成功**

Run: `python -c "import tests.conftest; print('conftest.py loaded successfully')"`
Expected: `conftest.py loaded successfully`

- [ ] **Step 4: 提交测试基础设施**

```bash
git add tests/conftest.py tests/data_collection/__init__.py
git commit -m "test: add shared fixtures and mock data generators

- Add comprehensive mock API responses for all 5 data sources
- Add sample factor data generator (16 factors, 30 days)
- Add temp directory fixtures for isolation
- Support pytest-mock for API isolation"
```

---

### Task 1.2: 数据校验模块

**Files:**
- Create: `src/data/validation.py`
- Create: `tests/data/test_validation.py`

- [ ] **Step 1: 编写数据校验测试**

```python
# tests/data/test_validation.py
"""Tests for data validation module."""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from src.data.validation import DataValidator, ValidationResult


class TestDataValidator:
    """Test DataValidator class."""
    
    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return DataValidator()
    
    def test_validate_coingecko_valid_data(self, validator, mock_coingecko_response):
        """Test valid CoinGecko data passes validation."""
        result = validator.validate('coingecko', mock_coingecko_response)
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_validate_coingecko_missing_required_field(self, validator, mock_coingecko_response):
        """Test missing required field fails validation."""
        data = mock_coingecko_response.copy()
        del data['current_price']
        result = validator.validate('coingecko', data)
        assert result.is_valid is False
        assert 'current_price' in str(result.errors)
    
    def test_validate_negative_value(self, validator, mock_coingecko_response):
        """Test negative value for positive-only field fails validation."""
        data = mock_coingecko_response.copy()
        data['market_cap'] = -1000
        result = validator.validate('coingecko', data)
        assert result.is_valid is False
        assert 'market_cap' in str(result.errors)
    
    def test_validate_invalid_timestamp(self, validator, mock_coingecko_response):
        """Test invalid timestamp format fails validation."""
        data = mock_coingecko_response.copy()
        data['last_updated'] = 'invalid_timestamp'
        result = validator.validate('coingecko', data)
        assert result.is_valid is False
        assert 'last_updated' in str(result.errors)
    
    def test_validate_coinglass_funding_rate(self, validator, mock_coinglass_response):
        """Test CoinGlass funding rate validation."""
        result = validator.validate('coinglass', mock_coinglass_response)
        assert result.is_valid is True
    
    def test_validate_defillama_tvl(self, validator, mock_defillama_response):
        """Test DefiLlama TVL validation."""
        result = validator.validate('defillama', mock_defillama_response)
        assert result.is_valid is True
    
    def test_validate_unknown_source(self, validator):
        """Test unknown data source raises error."""
        with pytest.raises(ValueError, match="Unknown data source"):
            validator.validate('unknown_source', {})
    
    def test_validate_dataframe_with_nan(self, validator):
        """Test DataFrame with NaN values handles gracefully."""
        df = pd.DataFrame({
            'price': [100.0, np.nan, 105.0],
            'volume': [1000, 2000, 3000]
        })
        result = validator.validate_dataframe(df, {'price': 'positive', 'volume': 'positive'})
        assert result.is_valid is True  # NaN is allowed
        assert 'price' in result.warnings  # Warning about NaN
    
    def test_validate_empty_data(self, validator):
        """Test empty data fails validation."""
        result = validator.validate('coingecko', {})
        assert result.is_valid is False
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/data/test_validation.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.data.validation'"

- [ ] **Step 3: 实现数据校验模块**

```python
# src/data/validation.py
"""Data validation module for API responses and collected data."""
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
import pandas as pd
import re


@dataclass
class ValidationResult:
    """Result of data validation."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def add_error(self, error: str):
        """Add validation error."""
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str):
        """Add validation warning."""
        self.warnings.append(warning)


class DataValidator:
    """Validate data from various API sources."""
    
    # Required fields per data source
    REQUIRED_FIELDS = {
        'coingecko': {
            'required': ['id', 'symbol', 'current_price', 'market_cap', 'market_cap_rank'],
            'positive': ['current_price', 'market_cap', 'total_volume', 'circulating_supply'],
            'timestamp': ['last_updated']
        },
        'coinglass': {
            'required': ['symbol', 'fundingRate', 'fundingTime'],
            'positive': [],  # funding rate can be negative
            'timestamp': ['fundingTime']
        },
        'defillama': {
            'required': ['chain', 'tvl'],
            'positive': ['tvl'],
            'timestamp': []
        },
        'github': {
            'required': ['id', 'name', 'full_name'],
            'positive': ['stargazers_count', 'forks_count', 'open_issues_count'],
            'timestamp': ['pushed_at', 'updated_at']
        },
        'reddit': {
            'required': ['kind', 'data'],
            'positive': [],
            'timestamp': []
        }
    }
    
    # Timestamp format patterns
    TIMESTAMP_PATTERNS = [
        r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',  # ISO format
        r'\d{4}-\d{2}-\d{2}',  # Date only
    ]
    
    def validate(self, source: str, data: Dict[str, Any]) -> ValidationResult:
        """Validate data from a specific source.
        
        Args:
            source: Data source name (coingecko, coinglass, etc.)
            data: Data dictionary to validate
            
        Returns:
            ValidationResult with is_valid, errors, and warnings
        """
        result = ValidationResult(is_valid=True)
        
        if source not in self.REQUIRED_FIELDS:
            raise ValueError(f"Unknown data source: {source}")
        
        schema = self.REQUIRED_FIELDS[source]
        
        # Check required fields
        for field_name in schema['required']:
            if field_name not in data:
                result.add_error(f"Missing required field: {field_name}")
        
        # Check positive-only fields
        for field_name in schema['positive']:
            if field_name in data:
                value = data[field_name]
                if isinstance(value, (int, float)) and value < 0:
                    result.add_error(f"Field {field_name} must be non-negative, got: {value}")
        
        # Validate timestamp fields
        for field_name in schema['timestamp']:
            if field_name in data:
                if not self._validate_timestamp(data[field_name]):
                    result.add_error(f"Invalid timestamp format for {field_name}: {data[field_name]}")
        
        return result
    
    def validate_dataframe(
        self, 
        df: pd.DataFrame, 
        field_rules: Dict[str, str]
    ) -> ValidationResult:
        """Validate a DataFrame based on field rules.
        
        Args:
            df: DataFrame to validate
            field_rules: Dict mapping column names to validation rules
                         Rules: 'positive', 'required', 'timestamp'
        
        Returns:
            ValidationResult
        """
        result = ValidationResult(is_valid=True)
        
        for column, rule in field_rules.items():
            if column not in df.columns:
                if rule == 'required':
                    result.add_error(f"Missing required column: {column}")
                continue
            
            # Check for NaN values
            nan_count = df[column].isna().sum()
            if nan_count > 0:
                result.add_warning(f"Column {column} has {nan_count} NaN values")
            
            # Check positive constraint
            if rule == 'positive':
                valid_values = df[column].dropna()
                if (valid_values < 0).any():
                    result.add_error(f"Column {column} contains negative values")
        
        return result
    
    def _validate_timestamp(self, value: Any) -> bool:
        """Validate timestamp format.
        
        Args:
            value: Timestamp value (string or numeric)
            
        Returns:
            True if valid, False otherwise
        """
        if isinstance(value, (int, float)):
            # Unix timestamp (seconds or milliseconds)
            try:
                # Assume milliseconds if > 1e12
                if value > 1e12:
                    datetime.fromtimestamp(value / 1000)
                else:
                    datetime.fromtimestamp(value)
                return True
            except (OSError, OverflowError):
                return False
        
        if isinstance(value, str):
            # Check against patterns
            for pattern in self.TIMESTAMP_PATTERNS:
                if re.match(pattern, value):
                    return True
            return False
        
        return False
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/data/test_validation.py -v`
Expected: All tests PASS

- [ ] **Step 5: 提交数据校验模块**

```bash
git add src/data/validation.py tests/data/test_validation.py
git commit -m "feat: add data validation module with comprehensive checks

- Add DataValidator with source-specific field validation
- Validate required fields, positive constraints, timestamps
- Support both dict and DataFrame validation
- Add detailed ValidationResult with errors and warnings
- Tests: 10 test cases covering all validation scenarios"
```

---

## 执行顺序总结

**阶段1 (Day 0-3):** 数据采集 + 测试基础设施
**阶段2 (Day 8-14):** 可视化 + 回测框架  
**阶段3 (Day 15+):** 鲸鱼监控 + 多币种分析

每个阶段包含完整的测试用例和验收标准。
