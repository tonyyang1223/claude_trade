# 市场数据采集器 (Market Data Collector) 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个自动化市场数据采集系统，从CoinMarketCap和CoinGecko获取数字货币的市值、价格、交易量等数据，支持缓存和数据导出。

**Architecture:** 采用分层架构 - API Client层负责与外部API通信，Data Model层定义数据结构，Cache层管理本地缓存，Collector层协调整个数据采集流程。使用pydantic进行数据验证，支持JSON和CSV导出。

**Tech Stack:** Python 3.10+, pydantic, requests, pycoingecko, python-coinmarketcap, pandas, pytest

---

## 文件结构

```
src/
├── __init__.py
├── data/
│   ├── __init__.py
│   ├── models.py          # 数据模型定义
│   ├── cache.py           # 缓存管理
│   └── exporters.py       # 数据导出器
├── api/
│   ├── __init__.py
│   ├── base.py            # API基类
│   ├── coingecko.py       # CoinGecko客户端
│   └── coinmarketcap.py   # CoinMarketCap客户端
└── collector/
    ├── __init__.py
    └── market_collector.py # 主采集器

tests/
├── __init__.py
├── test_models.py
├── test_cache.py
├── test_coingecko.py
├── test_coinmarketcap.py
└── test_market_collector.py

scripts/data_collection/
└── collect_market_data.py # 命令行入口
```

---

## Task 1: 项目依赖和配置

**Files:**
- Modify: `requirements.txt`
- Create: `.env.example`

- [ ] **Step 1: 添加新依赖到requirements.txt**

在现有requirements.txt末尾添加：

```
# API Clients
pycoingecko>=3.1.0
python-coinmarketcap>=0.2.0

# Data Validation
pydantic>=2.0.0

# Testing
pytest>=7.4.0
pytest-cov>=4.1.0
responses>=0.23.0
```

- [ ] **Step 2: 创建环境变量模板**

创建 `.env.example` 文件：

```
# CoinMarketCap API Key (free tier: 333 calls/day)
CMC_API_KEY=your_cmc_api_key_here

# CoinGecko API Key (optional, increases rate limit)
COINGECKO_API_KEY=

# Cache settings
CACHE_DIR=data/cache
CACHE_EXPIRE_HOURS=24
```

- [ ] **Step 3: 更新.gitignore**

在.gitignore中确保包含：

```
# Environment
.env

# Cache
data/cache/*
!data/cache/.gitkeep
```

- [ ] **Step 4: 提交配置更改**

```bash
git add requirements.txt .env.example .gitignore
git commit -m "$(cat <<'EOF'
chore: 添加市场数据采集器依赖配置

- 添加pycoingecko和python-coinmarketcap依赖
- 添加pydantic数据验证库
- 添加pytest测试框架
- 创建环境变量模板

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: 数据模型定义

**Files:**
- Create: `src/__init__.py`
- Create: `src/data/__init__.py`
- Create: `src/data/models.py`
- Create: `tests/__init__.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: 写失败的测试**

创建 `tests/__init__.py`（空文件）

创建 `tests/test_models.py`：

```python
"""Tests for data models."""
import pytest
from datetime import datetime
from src.data.models import CoinData, MarketData


class TestCoinData:
    """Tests for CoinData model."""
    
    def test_create_coin_data(self):
        """Test creating a CoinData instance."""
        coin = CoinData(
            id="bitcoin",
            symbol="BTC",
            name="Bitcoin",
            current_price=50000.0,
            market_cap=1000000000000.0,
            market_cap_rank=1,
            total_volume=50000000000.0,
            circulating_supply=19000000.0,
            total_supply=21000000.0,
            max_supply=21000000.0,
            price_change_24h=1000.0,
            price_change_percentage_24h=2.0,
            last_updated=datetime(2024, 1, 1, 12, 0, 0)
        )
        assert coin.id == "bitcoin"
        assert coin.symbol == "BTC"
        assert coin.current_price == 50000.0
        assert coin.market_cap_rank == 1
    
    def test_coin_data_required_fields(self):
        """Test that required fields are enforced."""
        with pytest.raises(Exception):
            CoinData()  # Should raise validation error
    
    def test_coin_data_optional_fields(self):
        """Test optional fields have defaults."""
        coin = CoinData(
            id="test-coin",
            symbol="TEST",
            name="Test Coin",
            current_price=1.0,
            market_cap=1000.0,
            market_cap_rank=100
        )
        assert coin.total_volume is None
        assert coin.max_supply is None


class TestMarketData:
    """Tests for MarketData model."""
    
    def test_create_market_data(self):
        """Test creating a MarketData instance."""
        coin = CoinData(
            id="bitcoin",
            symbol="BTC",
            name="Bitcoin",
            current_price=50000.0,
            market_cap=1000000000000.0,
            market_cap_rank=1
        )
        market = MarketData(
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            total_market_cap=2000000000000.0,
            btc_dominance=50.0,
            eth_dominance=20.0,
            coins=[coin]
        )
        assert market.btc_dominance == 50.0
        assert len(market.coins) == 1
    
    def test_market_data_default_timestamp(self):
        """Test that timestamp defaults to now."""
        market = MarketData(
            total_market_cap=1000000000000.0,
            btc_dominance=50.0
        )
        assert market.timestamp is not None
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_models.py -v
```

Expected: FAIL - ModuleNotFoundError: No module named 'src'

- [ ] **Step 3: 创建包初始化文件**

创建 `src/__init__.py`：

```python
"""Cryptocurrency Trading Research Package."""
__version__ = "0.1.0"
```

创建 `src/data/__init__.py`：

```python
"""Data models and utilities."""
from src.data.models import CoinData, MarketData

__all__ = ["CoinData", "MarketData"]
```

- [ ] **Step 4: 运行测试验证失败**

```bash
pytest tests/test_models.py -v
```

Expected: FAIL - ImportError: cannot import name 'CoinData'

- [ ] **Step 5: 实现数据模型**

创建 `src/data/models.py`：

```python
"""Data models for cryptocurrency market data."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class CoinData(BaseModel):
    """Represents data for a single cryptocurrency.
    
    Attributes:
        id: Unique identifier (e.g., 'bitcoin')
        symbol: Trading symbol (e.g., 'BTC')
        name: Full name (e.g., 'Bitcoin')
        current_price: Current price in USD
        market_cap: Market capitalization in USD
        market_cap_rank: Ranking by market cap
        total_volume: 24h trading volume in USD
        circulating_supply: Coins in circulation
        total_supply: Total coins that will ever exist
        max_supply: Maximum supply cap
        price_change_24h: Absolute price change in 24h
        price_change_percentage_24h: Percentage change in 24h
        last_updated: When data was last updated
    """
    id: str
    symbol: str
    name: str
    current_price: float
    market_cap: float
    market_cap_rank: int
    total_volume: Optional[float] = None
    circulating_supply: Optional[float] = None
    total_supply: Optional[float] = None
    max_supply: Optional[float] = None
    price_change_24h: Optional[float] = None
    price_change_percentage_24h: Optional[float] = None
    last_updated: Optional[datetime] = None
    
    model_config = {
        "json_schema_extra": {
            "examples": [{
                "id": "bitcoin",
                "symbol": "BTC",
                "name": "Bitcoin",
                "current_price": 50000.0,
                "market_cap": 1000000000000.0,
                "market_cap_rank": 1
            }]
        }
    }


class MarketData(BaseModel):
    """Represents overall market data snapshot.
    
    Attributes:
        timestamp: When this data was collected
        total_market_cap: Total crypto market cap
        btc_dominance: Bitcoin's market share percentage
        eth_dominance: Ethereum's market share percentage
        coins: List of top coins data
    """
    timestamp: datetime = Field(default_factory=datetime.now)
    total_market_cap: float
    btc_dominance: float
    eth_dominance: Optional[float] = None
    coins: List[CoinData] = Field(default_factory=list)
    
    model_config = {
        "json_schema_extra": {
            "examples": [{
                "total_market_cap": 2000000000000.0,
                "btc_dominance": 50.0,
                "eth_dominance": 20.0
            }]
        }
    }
```

- [ ] **Step 6: 运行测试验证通过**

```bash
pytest tests/test_models.py -v
```

Expected: PASS - All tests pass

- [ ] **Step 7: 提交数据模型**

```bash
git add src/__init__.py src/data/__init__.py src/data/models.py tests/__init__.py tests/test_models.py
git commit -m "$(cat <<'EOF'
feat: 添加数字货币数据模型

- CoinData模型：单个币种的详细数据
- MarketData模型：市场整体数据快照
- 包含完整的类型注解和文档
- 通过pytest测试验证

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: 缓存系统实现

**Files:**
- Create: `src/data/cache.py`
- Create: `tests/test_cache.py`

- [ ] **Step 1: 写失败的测试**

创建 `tests/test_cache.py`：

```python
"""Tests for cache system."""
import pytest
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from src.data.cache import DataCache


class TestDataCache:
    """Tests for DataCache class."""
    
    def test_cache_initialization(self, tmp_path):
        """Test cache initializes with correct directory."""
        cache = DataCache(cache_dir=tmp_path)
        assert cache.cache_dir == tmp_path
        assert tmp_path.exists()
    
    def test_save_and_load_data(self, tmp_path):
        """Test saving and loading data."""
        cache = DataCache(cache_dir=tmp_path)
        test_data = {"key": "value", "number": 123}
        
        cache.save("test_key", test_data)
        loaded = cache.load("test_key")
        
        assert loaded == test_data
    
    def test_cache_key_generates_filename(self, tmp_path):
        """Test that cache key generates proper filename."""
        cache = DataCache(cache_dir=tmp_path)
        filename = cache._get_cache_path("bitcoin_market")
        
        assert filename.suffix == ".json"
        assert "bitcoin_market" in str(filename)
    
    def test_cache_expiry(self, tmp_path):
        """Test that expired cache returns None."""
        cache = DataCache(cache_dir=tmp_path, expire_hours=1)
        test_data = {"key": "value"}
        
        # Save data
        cache.save("test_key", test_data)
        
        # Modify file time to simulate expiry
        cache_path = cache._get_cache_path("test_key")
        old_time = datetime.now() - timedelta(hours=2)
        os.utime(cache_path, (old_time.timestamp(), old_time.timestamp()))
        
        # Should return None for expired cache
        loaded = cache.load("test_key")
        assert loaded is None
    
    def test_cache_not_expired(self, tmp_path):
        """Test that fresh cache returns data."""
        cache = DataCache(cache_dir=tmp_path, expire_hours=24)
        test_data = {"key": "value"}
        
        cache.save("test_key", test_data)
        loaded = cache.load("test_key")
        
        assert loaded == test_data
    
    def test_clear_cache(self, tmp_path):
        """Test clearing cache."""
        cache = DataCache(cache_dir=tmp_path)
        cache.save("key1", {"a": 1})
        cache.save("key2", {"b": 2})
        
        cache.clear()
        
        assert cache.load("key1") is None
        assert cache.load("key2") is None
    
    def test_cache_missing_file(self, tmp_path):
        """Test loading non-existent cache returns None."""
        cache = DataCache(cache_dir=tmp_path)
        loaded = cache.load("nonexistent")
        assert loaded is None
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_cache.py -v
```

Expected: FAIL - ImportError: cannot import name 'DataCache'

- [ ] **Step 3: 实现缓存系统**

创建 `src/data/cache.py`：

```python
"""Cache system for market data."""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional


class DataCache:
    """Manages local file-based cache for market data.
    
    Attributes:
        cache_dir: Directory to store cache files
        expire_hours: Hours before cache expires
    
    Example:
        >>> cache = DataCache(Path("data/cache"), expire_hours=24)
        >>> cache.save("btc_price", {"price": 50000})
        >>> data = cache.load("btc_price")
    """
    
    def __init__(
        self, 
        cache_dir: Path = Path("data/cache"),
        expire_hours: int = 24
    ):
        """Initialize cache system.
        
        Args:
            cache_dir: Directory to store cache files
            expire_hours: Hours before cache is considered stale
        """
        self.cache_dir = Path(cache_dir)
        self.expire_hours = expire_hours
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_path(self, key: str) -> Path:
        """Get file path for a cache key.
        
        Args:
            key: Cache key identifier
            
        Returns:
            Path to cache file
        """
        safe_key = key.replace("/", "_").replace("\\", "_")
        return self.cache_dir / f"{safe_key}.json"
    
    def save(self, key: str, data: Any) -> None:
        """Save data to cache.
        
        Args:
            key: Cache key identifier
            data: Data to cache (must be JSON serializable)
        """
        cache_path = self._get_cache_path(key)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load(self, key: str) -> Optional[Any]:
        """Load data from cache.
        
        Args:
            key: Cache key identifier
            
        Returns:
            Cached data if valid, None if missing or expired
        """
        cache_path = self._get_cache_path(key)
        
        if not cache_path.exists():
            return None
        
        # Check if cache is expired
        mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
        if datetime.now() - mtime > timedelta(hours=self.expire_hours):
            return None
        
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def clear(self) -> None:
        """Clear all cached data."""
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_cache.py -v
```

Expected: PASS - All tests pass

- [ ] **Step 5: 提交缓存系统**

```bash
git add src/data/cache.py tests/test_cache.py
git commit -m "$(cat <<'EOF'
feat: 添加数据缓存系统

- DataCache类：基于文件的缓存管理
- 支持缓存过期时间设置
- 支持缓存清理
- 完整的单元测试覆盖

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: API基类实现

**Files:**
- Create: `src/api/__init__.py`
- Create: `src/api/base.py`
- Create: `tests/test_api_base.py`

- [ ] **Step 1: 写失败的测试**

创建 `tests/test_api_base.py`：

```python
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
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_api_base.py -v
```

Expected: FAIL - ImportError: cannot import name 'BaseAPIClient'

- [ ] **Step 3: 实现API基类**

创建 `src/api/__init__.py`：

```python
"""API clients for cryptocurrency data sources."""
from src.api.base import BaseAPIClient

__all__ = ["BaseAPIClient"]
```

创建 `src/api/base.py`：

```python
"""Base class for API clients."""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


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
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_api_base.py -v
```

Expected: PASS - All tests pass

- [ ] **Step 5: 提交API基类**

```bash
git add src/api/__init__.py src/api/base.py tests/test_api_base.py
git commit -m "$(cat <<'EOF'
feat: 添加API客户端基类

- BaseAPIClient抽象基类
- 定义统一的数据获取接口
- 强制子类实现核心方法

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: CoinGecko API客户端

**Files:**
- Create: `src/api/coingecko.py`
- Create: `tests/test_coingecko.py`

- [ ] **Step 1: 写失败的测试**

创建 `tests/test_coingecko.py`：

```python
"""Tests for CoinGecko API client."""
import pytest
import responses
from unittest.mock import patch, MagicMock
from src.api.coingecko import CoinGeckoClient


class TestCoinGeckoClient:
    """Tests for CoinGeckoClient class."""
    
    def test_client_initialization(self):
        """Test client initializes without API key."""
        client = CoinGeckoClient()
        assert client is not None
    
    def test_client_with_api_key(self):
        """Test client initializes with API key."""
        client = CoinGeckoClient(api_key="test_key")
        assert client.api_key == "test_key"
    
    @responses.activate
    def test_get_coin_data(self):
        """Test getting single coin data."""
        mock_response = {
            "id": "bitcoin",
            "symbol": "btc",
            "name": "Bitcoin",
            "market_data": {
                "current_price": {"usd": 50000},
                "market_cap": {"usd": 1000000000000},
                "market_cap_rank": 1,
                "total_volume": {"usd": 50000000000},
                "circulating_supply": 19000000,
                "total_supply": 21000000,
                "max_supply": 21000000,
                "price_change_24h": 1000,
                "price_change_percentage_24h": 2.0
            },
            "last_updated": "2024-01-01T12:00:00Z"
        }
        
        responses.add(
            responses.GET,
            "https://api.coingecko.com/api/v3/coins/bitcoin",
            json=mock_response,
            status=200
        )
        
        client = CoinGeckoClient()
        data = client.get_coin_data("bitcoin")
        
        assert data["id"] == "bitcoin"
        assert data["symbol"] == "btc"
    
    @responses.activate
    def test_get_market_data(self):
        """Test getting market data."""
        mock_response = {
            "data": {
                "total_market_cap": {"usd": 2000000000000},
                "market_cap_percentage": {
                    "btc": 50.0,
                    "eth": 20.0
                }
            }
        }
        
        responses.add(
            responses.GET,
            "https://api.coingecko.com/api/v3/global",
            json=mock_response,
            status=200
        )
        
        client = CoinGeckoClient()
        data = client.get_market_data()
        
        assert "total_market_cap" in data
        assert "btc_dominance" in data
    
    @responses.activate
    def test_get_top_coins(self):
        """Test getting top coins list."""
        mock_response = [
            {
                "id": "bitcoin",
                "symbol": "btc",
                "name": "Bitcoin",
                "current_price": 50000,
                "market_cap": 1000000000000,
                "market_cap_rank": 1,
                "total_volume": 50000000000
            }
        ]
        
        responses.add(
            responses.GET,
            "https://api.coingecko.com/api/v3/coins/markets",
            json=mock_response,
            status=200
        )
        
        client = CoinGeckoClient()
        coins = client.get_top_coins(limit=1)
        
        assert len(coins) == 1
        assert coins[0]["id"] == "bitcoin"
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_coingecko.py -v
```

Expected: FAIL - ImportError: cannot import name 'CoinGeckoClient'

- [ ] **Step 3: 实现CoinGecko客户端**

创建 `src/api/coingecko.py`：

```python
"""CoinGecko API client implementation."""
import requests
from typing import List, Dict, Any, Optional
from src.api.base import BaseAPIClient


class CoinGeckoClient(BaseAPIClient):
    """Client for CoinGecko API.
    
    Free tier: 50 calls/minute
    API key increases rate limit significantly.
    
    Attributes:
        api_key: Optional API key for higher rate limits
        base_url: API base URL
        
    Example:
        >>> client = CoinGeckoClient()
        >>> btc_data = client.get_coin_data("bitcoin")
    """
    
    BASE_URL = "https://api.coingecko.com/api/v3"
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize CoinGecko client.
        
        Args:
            api_key: Optional API key for higher rate limits
        """
        self.api_key = api_key
        self.session = requests.Session()
        
        if api_key:
            self.session.headers.update({"x-api-key": api_key})
    
    def get_coin_data(self, coin_id: str) -> Dict[str, Any]:
        """Get detailed data for a single coin.
        
        Args:
            coin_id: CoinGecko coin ID (e.g., 'bitcoin')
            
        Returns:
            Dictionary with coin data
        """
        url = f"{self.BASE_URL}/coins/{coin_id}"
        params = {
            "localization": "false",
            "tickers": "false",
            "community_data": "false",
            "developer_data": "false"
        }
        
        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        market_data = data.get("market_data", {})
        
        return {
            "id": data.get("id"),
            "symbol": data.get("symbol", "").upper(),
            "name": data.get("name"),
            "current_price": market_data.get("current_price", {}).get("usd"),
            "market_cap": market_data.get("market_cap", {}).get("usd"),
            "market_cap_rank": data.get("market_cap_rank"),
            "total_volume": market_data.get("total_volume", {}).get("usd"),
            "circulating_supply": market_data.get("circulating_supply"),
            "total_supply": market_data.get("total_supply"),
            "max_supply": market_data.get("max_supply"),
            "price_change_24h": market_data.get("price_change_24h"),
            "price_change_percentage_24h": market_data.get("price_change_percentage_24h"),
            "last_updated": data.get("last_updated")
        }
    
    def get_market_data(self) -> Dict[str, Any]:
        """Get global market data.
        
        Returns:
            Dictionary with market data including dominance
        """
        url = f"{self.BASE_URL}/global"
        
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        
        data = response.json().get("data", {})
        market_cap_percentage = data.get("market_cap_percentage", {})
        
        return {
            "total_market_cap": data.get("total_market_cap", {}).get("usd"),
            "total_volume": data.get("total_volume", {}).get("usd"),
            "btc_dominance": market_cap_percentage.get("btc"),
            "eth_dominance": market_cap_percentage.get("eth"),
            "market_cap_percentage": market_cap_percentage,
            "active_cryptocurrencies": data.get("active_cryptocurrencies"),
            "markets": data.get("markets")
        }
    
    def get_top_coins(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get top coins by market cap.
        
        Args:
            limit: Number of coins to retrieve (max 250)
            
        Returns:
            List of coin data dictionaries
        """
        url = f"{self.BASE_URL}/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": min(limit, 250),
            "page": 1,
            "sparkline": "false"
        }
        
        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        coins = response.json()
        
        return [
            {
                "id": coin.get("id"),
                "symbol": coin.get("symbol", "").upper(),
                "name": coin.get("name"),
                "current_price": coin.get("current_price"),
                "market_cap": coin.get("market_cap"),
                "market_cap_rank": coin.get("market_cap_rank"),
                "total_volume": coin.get("total_volume"),
                "circulating_supply": coin.get("circulating_supply"),
                "total_supply": coin.get("total_supply"),
                "max_supply": coin.get("max_supply"),
                "price_change_24h": coin.get("price_change_24h"),
                "price_change_percentage_24h": coin.get("price_change_percentage_24h"),
                "last_updated": coin.get("last_updated")
            }
            for coin in coins
        ]
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_coingecko.py -v
```

Expected: PASS - All tests pass

- [ ] **Step 5: 提交CoinGecko客户端**

```bash
git add src/api/coingecko.py tests/test_coingecko.py
git commit -m "$(cat <<'EOF'
feat: 添加CoinGecko API客户端

- CoinGeckoClient类实现
- 支持获取单个币种数据
- 支持获取市场整体数据
- 支持获取市值排名前列币种
- 使用responses库进行API模拟测试

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: CoinMarketCap API客户端

**Files:**
- Create: `src/api/coinmarketcap.py`
- Create: `tests/test_coinmarketcap.py`

- [ ] **Step 1: 写失败的测试**

创建 `tests/test_coinmarketcap.py`：

```python
"""Tests for CoinMarketCap API client."""
import pytest
import responses
from src.api.coinmarketcap import CoinMarketCapClient


class TestCoinMarketCapClient:
    """Tests for CoinMarketCapClient class."""
    
    def test_client_requires_api_key(self):
        """Test that client requires API key."""
        with pytest.raises(ValueError):
            CoinMarketCapClient()
    
    def test_client_with_api_key(self):
        """Test client initializes with API key."""
        client = CoinMarketCapClient(api_key="test_key")
        assert client.api_key == "test_key"
    
    @responses.activate
    def test_get_coin_data(self):
        """Test getting single coin data."""
        mock_response = {
            "data": {
                "1": {
                    "id": 1,
                    "symbol": "BTC",
                    "name": "Bitcoin",
                    "quote": {
                        "USD": {
                            "price": 50000.0,
                            "market_cap": 1000000000000.0,
                            "volume_24h": 50000000000.0,
                            "percent_change_24h": 2.0
                        }
                    },
                    "circulating_supply": 19000000,
                    "total_supply": 21000000,
                    "max_supply": 21000000,
                    "cmc_rank": 1
                }
            }
        }
        
        responses.add(
            responses.GET,
            "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest",
            json=mock_response,
            status=200
        )
        
        client = CoinMarketCapClient(api_key="test_key")
        data = client.get_coin_data("bitcoin")
        
        assert data["symbol"] == "BTC"
    
    @responses.activate
    def test_get_market_data(self):
        """Test getting market data."""
        mock_response = {
            "data": {
                "total_market_cap": {"USD": 2000000000000},
                "btc_dominance": 50.0,
                "eth_dominance": 20.0
            }
        }
        
        responses.add(
            responses.GET,
            "https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest",
            json=mock_response,
            status=200
        )
        
        client = CoinMarketCapClient(api_key="test_key")
        data = client.get_market_data()
        
        assert data["btc_dominance"] == 50.0
    
    @responses.activate
    def test_get_top_coins(self):
        """Test getting top coins."""
        mock_response = {
            "data": [
                {
                    "id": 1,
                    "symbol": "BTC",
                    "name": "Bitcoin",
                    "cmc_rank": 1,
                    "quote": {
                        "USD": {
                            "price": 50000.0,
                            "market_cap": 1000000000000.0,
                            "volume_24h": 50000000000.0,
                            "percent_change_24h": 2.0
                        }
                    },
                    "circulating_supply": 19000000,
                    "total_supply": 21000000
                }
            ]
        }
        
        responses.add(
            responses.GET,
            "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest",
            json=mock_response,
            status=200
        )
        
        client = CoinMarketCapClient(api_key="test_key")
        coins = client.get_top_coins(limit=1)
        
        assert len(coins) == 1
        assert coins[0]["symbol"] == "BTC"
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_coinmarketcap.py -v
```

Expected: FAIL - ImportError: cannot import name 'CoinMarketCapClient'

- [ ] **Step 3: 实现CoinMarketCap客户端**

创建 `src/api/coinmarketcap.py`：

```python
"""CoinMarketCap API client implementation."""
import requests
from typing import List, Dict, Any, Optional
from src.api.base import BaseAPIClient


class CoinMarketCapClient(BaseAPIClient):
    """Client for CoinMarketCap API.
    
    Requires API key (free tier: 333 calls/day).
    
    Attributes:
        api_key: CMC API key (required)
        base_url: API base URL
        
    Example:
        >>> client = CoinMarketCapClient(api_key="your_key")
        >>> btc_data = client.get_coin_data("bitcoin")
    """
    
    BASE_URL = "https://pro-api.coinmarketcap.com/v1"
    
    def __init__(self, api_key: str):
        """Initialize CMC client.
        
        Args:
            api_key: CoinMarketCap API key (required)
            
        Raises:
            ValueError: If api_key is not provided
        """
        if not api_key:
            raise ValueError("CoinMarketCap API key is required")
        
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "X-CMC_PRO_API_KEY": api_key,
            "Accept": "application/json"
        })
    
    def get_coin_data(self, coin_id: str) -> Dict[str, Any]:
        """Get data for a single coin.
        
        Args:
            coin_id: CMC coin ID or symbol (e.g., 'bitcoin' or 'BTC')
            
        Returns:
            Dictionary with coin data
        """
        url = f"{self.BASE_URL}/cryptocurrency/quotes/latest"
        params = {"symbol": coin_id.upper()}
        
        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json().get("data", {})
        
        # Get first coin from response
        coin_data = list(data.values())[0] if data else {}
        quote = coin_data.get("quote", {}).get("USD", {})
        
        return {
            "id": coin_data.get("id"),
            "symbol": coin_data.get("symbol"),
            "name": coin_data.get("name"),
            "current_price": quote.get("price"),
            "market_cap": quote.get("market_cap"),
            "market_cap_rank": coin_data.get("cmc_rank"),
            "total_volume": quote.get("volume_24h"),
            "circulating_supply": coin_data.get("circulating_supply"),
            "total_supply": coin_data.get("total_supply"),
            "max_supply": coin_data.get("max_supply"),
            "price_change_24h": quote.get("price_change_24h"),
            "price_change_percentage_24h": quote.get("percent_change_24h"),
            "last_updated": quote.get("last_updated")
        }
    
    def get_market_data(self) -> Dict[str, Any]:
        """Get global market data.
        
        Returns:
            Dictionary with market data
        """
        url = f"{self.BASE_URL}/global-metrics/quotes/latest"
        
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        
        data = response.json().get("data", {})
        
        return {
            "total_market_cap": data.get("total_market_cap", {}).get("USD"),
            "total_volume": data.get("total_volume_24h", {}).get("USD"),
            "btc_dominance": data.get("btc_dominance"),
            "eth_dominance": data.get("eth_dominance"),
            "active_cryptocurrencies": data.get("active_cryptocurrencies"),
            "markets": data.get("active_market_pairs")
        }
    
    def get_top_coins(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get top coins by market cap.
        
        Args:
            limit: Number of coins to retrieve (max 5000)
            
        Returns:
            List of coin data dictionaries
        """
        url = f"{self.BASE_URL}/cryptocurrency/listings/latest"
        params = {
            "limit": min(limit, 5000),
            "sort": "market_cap",
            "sort_dir": "desc"
        }
        
        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        coins = response.json().get("data", [])
        
        return [
            {
                "id": coin.get("id"),
                "symbol": coin.get("symbol"),
                "name": coin.get("name"),
                "current_price": coin.get("quote", {}).get("USD", {}).get("price"),
                "market_cap": coin.get("quote", {}).get("USD", {}).get("market_cap"),
                "market_cap_rank": coin.get("cmc_rank"),
                "total_volume": coin.get("quote", {}).get("USD", {}).get("volume_24h"),
                "circulating_supply": coin.get("circulating_supply"),
                "total_supply": coin.get("total_supply"),
                "max_supply": coin.get("max_supply"),
                "price_change_24h": coin.get("quote", {}).get("USD", {}).get("price_change_24h"),
                "price_change_percentage_24h": coin.get("quote", {}).get("USD", {}).get("percent_change_24h"),
                "last_updated": coin.get("quote", {}).get("USD", {}).get("last_updated")
            }
            for coin in coins
        ]
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_coinmarketcap.py -v
```

Expected: PASS - All tests pass

- [ ] **Step 5: 提交CoinMarketCap客户端**

```bash
git add src/api/coinmarketcap.py tests/test_coinmarketcap.py
git commit -m "$(cat <<'EOF'
feat: 添加CoinMarketCap API客户端

- CoinMarketCapClient类实现
- 必须提供API密钥
- 支持获取单个币种数据
- 支持获取市场整体数据
- 支持获取市值排名前列币种
- 完整的API模拟测试

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: 数据导出器

**Files:**
- Create: `src/data/exporters.py`
- Create: `tests/test_exporters.py`

- [ ] **Step 1: 写失败的测试**

创建 `tests/test_exporters.py`：

```python
"""Tests for data exporters."""
import pytest
import json
import pandas as pd
from pathlib import Path
from src.data.exporters import DataExporter
from src.data.models import CoinData, MarketData
from datetime import datetime


class TestDataExporter:
    """Tests for DataExporter class."""
    
    def test_export_to_json(self, tmp_path):
        """Test exporting to JSON file."""
        exporter = DataExporter(output_dir=tmp_path)
        
        coin = CoinData(
            id="bitcoin",
            symbol="BTC",
            name="Bitcoin",
            current_price=50000.0,
            market_cap=1000000000000.0,
            market_cap_rank=1
        )
        
        output_file = exporter.to_json([coin.dict()], "test_output")
        
        assert output_file.exists()
        assert output_file.suffix == ".json"
        
        with open(output_file) as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["id"] == "bitcoin"
    
    def test_export_to_csv(self, tmp_path):
        """Test exporting to CSV file."""
        exporter = DataExporter(output_dir=tmp_path)
        
        coin = CoinData(
            id="bitcoin",
            symbol="BTC",
            name="Bitcoin",
            current_price=50000.0,
            market_cap=1000000000000.0,
            market_cap_rank=1
        )
        
        output_file = exporter.to_csv([coin.dict()], "test_output")
        
        assert output_file.exists()
        assert output_file.suffix == ".csv"
        
        df = pd.read_csv(output_file)
        assert len(df) == 1
        assert df.iloc[0]["id"] == "bitcoin"
    
    def test_export_market_data_to_json(self, tmp_path):
        """Test exporting market data to JSON."""
        exporter = DataExporter(output_dir=tmp_path)
        
        market = MarketData(
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            total_market_cap=2000000000000.0,
            btc_dominance=50.0
        )
        
        output_file = exporter.to_json([market.dict()], "market_data")
        
        assert output_file.exists()
        
        with open(output_file) as f:
            data = json.load(f)
        assert data[0]["btc_dominance"] == 50.0
    
    def test_generate_timestamped_filename(self, tmp_path):
        """Test generating timestamped filename."""
        exporter = DataExporter(output_dir=tmp_path)
        filename = exporter._generate_filename("test", "json")
        
        assert filename.startswith("test_")
        assert filename.endswith(".json")
        assert len(filename) > 10  # Should have timestamp
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_exporters.py -v
```

Expected: FAIL - ImportError: cannot import name 'DataExporter'

- [ ] **Step 3: 实现数据导出器**

创建 `src/data/exporters.py`：

```python
"""Data export utilities."""
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd


class DataExporter:
    """Exports data to various formats.
    
    Attributes:
        output_dir: Directory for output files
        
    Example:
        >>> exporter = DataExporter(Path("data/processed"))
        >>> exporter.to_json(coins_data, "top_100_coins")
        >>> exporter.to_csv(market_data, "market_summary")
    """
    
    def __init__(self, output_dir: Path = Path("data/processed")):
        """Initialize exporter.
        
        Args:
            output_dir: Directory for output files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _generate_filename(self, prefix: str, extension: str) -> str:
        """Generate timestamped filename.
        
        Args:
            prefix: Filename prefix
            extension: File extension without dot
            
        Returns:
            Timestamped filename
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp}.{extension}"
    
    def to_json(
        self, 
        data: List[Dict[str, Any]], 
        prefix: str,
        pretty: bool = True
    ) -> Path:
        """Export data to JSON file.
        
        Args:
            data: List of dictionaries to export
            prefix: Filename prefix
            pretty: Whether to format JSON with indentation
            
        Returns:
            Path to created file
        """
        filename = self._generate_filename(prefix, "json")
        output_path = self.output_dir / filename
        
        with open(output_path, "w", encoding="utf-8") as f:
            if pretty:
                json.dump(data, f, ensure_ascii=False, indent=2)
            else:
                json.dump(data, f, ensure_ascii=False)
        
        return output_path
    
    def to_csv(
        self, 
        data: List[Dict[str, Any]], 
        prefix: str,
        index: bool = False
    ) -> Path:
        """Export data to CSV file.
        
        Args:
            data: List of dictionaries to export
            prefix: Filename prefix
            index: Whether to include DataFrame index
            
        Returns:
            Path to created file
        """
        filename = self._generate_filename(prefix, "csv")
        output_path = self.output_dir / filename
        
        df = pd.DataFrame(data)
        df.to_csv(output_path, index=index, encoding="utf-8")
        
        return output_path
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_exporters.py -v
```

Expected: PASS - All tests pass

- [ ] **Step 5: 提交数据导出器**

```bash
git add src/data/exporters.py tests/test_exporters.py
git commit -m "$(cat <<'EOF'
feat: 添加数据导出器

- DataExporter类：支持JSON和CSV导出
- 自动生成带时间戳的文件名
- 支持格式化输出
- 完整的单元测试

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: 主采集器整合

**Files:**
- Create: `src/collector/__init__.py`
- Create: `src/collector/market_collector.py`
- Create: `tests/test_market_collector.py`

- [ ] **Step 1: 写失败的测试**

创建 `tests/test_market_collector.py`：

```python
"""Tests for MarketCollector."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from src.collector.market_collector import MarketCollector
from src.data.models import CoinData, MarketData


class TestMarketCollector:
    """Tests for MarketCollector class."""
    
    def test_initialization_with_coingecko(self, tmp_path):
        """Test initializing with CoinGecko client."""
        with patch('src.collector.market_collector.CoinGeckoClient') as mock_client:
            collector = MarketCollector(
                api_source="coingecko",
                cache_dir=tmp_path
            )
            assert collector.api_source == "coingecko"
    
    def test_collect_market_data(self, tmp_path):
        """Test collecting market data."""
        mock_api = Mock()
        mock_api.get_market_data.return_value = {
            "total_market_cap": 2000000000000.0,
            "btc_dominance": 50.0,
            "eth_dominance": 20.0
        }
        mock_api.get_top_coins.return_value = [
            {
                "id": "bitcoin",
                "symbol": "BTC",
                "name": "Bitcoin",
                "current_price": 50000.0,
                "market_cap": 1000000000000.0,
                "market_cap_rank": 1
            }
        ]
        
        with patch('src.collector.market_collector.CoinGeckoClient', return_value=mock_api):
            collector = MarketCollector(
                api_source="coingecko",
                cache_dir=tmp_path
            )
            market_data = collector.collect_market_data(top_n=10)
            
            assert market_data is not None
            assert market_data.btc_dominance == 50.0
            assert len(market_data.coins) == 1
    
    def test_collect_single_coin(self, tmp_path):
        """Test collecting single coin data."""
        mock_api = Mock()
        mock_api.get_coin_data.return_value = {
            "id": "bitcoin",
            "symbol": "BTC",
            "name": "Bitcoin",
            "current_price": 50000.0,
            "market_cap": 1000000000000.0,
            "market_cap_rank": 1
        }
        
        with patch('src.collector.market_collector.CoinGeckoClient', return_value=mock_api):
            collector = MarketCollector(
                api_source="coingecko",
                cache_dir=tmp_path
            )
            coin_data = collector.collect_coin_data("bitcoin")
            
            assert coin_data.id == "bitcoin"
            assert coin_data.symbol == "BTC"
    
    def test_cache_is_used(self, tmp_path):
        """Test that cache is used when available."""
        mock_api = Mock()
        mock_cache = Mock()
        mock_cache.load.return_value = {
            "id": "bitcoin",
            "symbol": "BTC",
            "name": "Bitcoin",
            "current_price": 50000.0,
            "market_cap": 1000000000000.0,
            "market_cap_rank": 1
        }
        
        with patch('src.collector.market_collector.CoinGeckoClient', return_value=mock_api):
            with patch('src.collector.market_collector.DataCache', return_value=mock_cache):
                collector = MarketCollector(
                    api_source="coingecko",
                    cache_dir=tmp_path
                )
                coin_data = collector.collect_coin_data("bitcoin")
                
                # Should use cache, not API
                assert coin_data.symbol == "BTC"
                mock_api.get_coin_data.assert_not_called()
    
    def test_export_collected_data(self, tmp_path):
        """Test exporting collected data."""
        mock_api = Mock()
        mock_api.get_market_data.return_value = {
            "total_market_cap": 2000000000000.0,
            "btc_dominance": 50.0
        }
        mock_api.get_top_coins.return_value = []
        
        with patch('src.collector.market_collector.CoinGeckoClient', return_value=mock_api):
            collector = MarketCollector(
                api_source="coingecko",
                cache_dir=tmp_path
            )
            market_data = collector.collect_market_data()
            
            json_path = collector.export_data(market_data, format="json")
            csv_path = collector.export_data(market_data, format="csv")
            
            assert json_path.exists()
            assert csv_path.exists()
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/test_market_collector.py -v
```

Expected: FAIL - ImportError: cannot import name 'MarketCollector'

- [ ] **Step 3: 实现主采集器**

创建 `src/collector/__init__.py`：

```python
"""Data collection orchestrators."""
from src.collector.market_collector import MarketCollector

__all__ = ["MarketCollector"]
```

创建 `src/collector/market_collector.py`：

```python
"""Main market data collector."""
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from src.api.coingecko import CoinGeckoClient
from src.api.coinmarketcap import CoinMarketCapClient
from src.data.models import CoinData, MarketData
from src.data.cache import DataCache
from src.data.exporters import DataExporter


class MarketCollector:
    """Orchestrates market data collection.
    
    Coordinates API clients, caching, and data export.
    
    Attributes:
        api_source: Which API to use ('coingecko' or 'coinmarketcap')
        cache: DataCache instance
        exporter: DataExporter instance
        
    Example:
        >>> collector = MarketCollector(api_source="coingecko")
        >>> market_data = collector.collect_market_data(top_n=100)
        >>> collector.export_data(market_data, format="json")
    """
    
    def __init__(
        self,
        api_source: str = "coingecko",
        api_key: Optional[str] = None,
        cache_dir: Path = Path("data/cache"),
        output_dir: Path = Path("data/processed"),
        cache_expire_hours: int = 24
    ):
        """Initialize market collector.
        
        Args:
            api_source: API to use ('coingecko' or 'coinmarketcap')
            api_key: Optional API key
            cache_dir: Directory for cache files
            output_dir: Directory for exported files
            cache_expire_hours: Cache expiration time
        """
        self.api_source = api_source
        self.cache = DataCache(cache_dir, expire_hours=cache_expire_hours)
        self.exporter = DataExporter(output_dir)
        
        if api_source == "coingecko":
            self.api_client = CoinGeckoClient(api_key=api_key)
        elif api_source == "coinmarketcap":
            if not api_key:
                raise ValueError("CoinMarketCap requires API key")
            self.api_client = CoinMarketCapClient(api_key=api_key)
        else:
            raise ValueError(f"Unknown API source: {api_source}")
    
    def collect_coin_data(self, coin_id: str, use_cache: bool = True) -> CoinData:
        """Collect data for a single coin.
        
        Args:
            coin_id: Coin identifier
            use_cache: Whether to use cached data
            
        Returns:
            CoinData instance
        """
        cache_key = f"coin_{coin_id}"
        
        # Try cache first
        if use_cache:
            cached = self.cache.load(cache_key)
            if cached:
                return CoinData(**cached)
        
        # Fetch from API
        data = self.api_client.get_coin_data(coin_id)
        
        # Cache the result
        self.cache.save(cache_key, data)
        
        return CoinData(**data)
    
    def collect_market_data(self, top_n: int = 100, use_cache: bool = True) -> MarketData:
        """Collect overall market data.
        
        Args:
            top_n: Number of top coins to include
            use_cache: Whether to use cached data
            
        Returns:
            MarketData instance
        """
        # Get market data
        market_cache_key = "market_global"
        market_data = None
        
        if use_cache:
            cached = self.cache.load(market_cache_key)
            if cached:
                market_data = cached
        
        if not market_data:
            market_data = self.api_client.get_market_data()
            self.cache.save(market_cache_key, market_data)
        
        # Get top coins
        coins_cache_key = f"top_coins_{top_n}"
        coins_data = None
        
        if use_cache:
            cached = self.cache.load(coins_cache_key)
            if cached:
                coins_data = cached
        
        if not coins_data:
            coins_data = self.api_client.get_top_coins(limit=top_n)
            self.cache.save(coins_cache_key, coins_data)
        
        # Build MarketData
        coins = [CoinData(**coin) for coin in coins_data]
        
        return MarketData(
            timestamp=datetime.now(),
            total_market_cap=market_data.get("total_market_cap"),
            btc_dominance=market_data.get("btc_dominance"),
            eth_dominance=market_data.get("eth_dominance"),
            coins=coins
        )
    
    def export_data(
        self, 
        data: MarketData, 
        format: str = "json",
        prefix: str = "market_data"
    ) -> Path:
        """Export collected data.
        
        Args:
            data: MarketData to export
            format: Export format ('json' or 'csv')
            prefix: Filename prefix
            
        Returns:
            Path to exported file
        """
        # Convert to list of dicts
        data_dict = data.dict()
        
        if format == "json":
            return self.exporter.to_json([data_dict], prefix)
        elif format == "csv":
            # Flatten for CSV
            flat_data = {
                "timestamp": data_dict.get("timestamp"),
                "total_market_cap": data_dict.get("total_market_cap"),
                "btc_dominance": data_dict.get("btc_dominance"),
                "eth_dominance": data_dict.get("eth_dominance"),
                "coin_count": len(data_dict.get("coins", []))
            }
            return self.exporter.to_csv([flat_data], prefix)
        else:
            raise ValueError(f"Unknown format: {format}")
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/test_market_collector.py -v
```

Expected: PASS - All tests pass

- [ ] **Step 5: 提交主采集器**

```bash
git add src/collector/__init__.py src/collector/market_collector.py tests/test_market_collector.py
git commit -m "$(cat <<'EOF'
feat: 添加市场数据主采集器

- MarketCollector类：协调API、缓存和导出
- 支持CoinGecko和CoinMarketCap数据源
- 集成缓存系统提升效率
- 支持JSON和CSV导出
- 完整的单元测试

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: 命令行入口脚本

**Files:**
- Modify: `scripts/data_collection/collect_market_data.py`

- [ ] **Step 1: 实现命令行脚本**

修改 `scripts/data_collection/collect_market_data.py`：

```python
#!/usr/bin/env python3
"""Command-line interface for market data collection.

Usage:
    # Collect top 100 coins using CoinGecko (free)
    python scripts/data_collection/collect_market_data.py --source coingecko --top 100
    
    # Collect market data using CoinMarketCap (requires API key)
    python scripts/data_collection/collect_market_data.py --source coinmarketcap --api-key YOUR_KEY
    
    # Collect specific coin data
    python scripts/data_collection/collect_market_data.py --coin bitcoin --source coingecko
    
    # Export to CSV
    python scripts/data_collection/collect_market_data.py --source coingecko --format csv
"""
import argparse
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from src.collector.market_collector import MarketCollector


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Collect cryptocurrency market data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --source coingecko --top 100
  %(prog)s --source coinmarketcap --api-key YOUR_KEY
  %(prog)s --coin bitcoin ethereum
  %(prog)s --source coingecko --format csv --no-cache
        """
    )
    
    parser.add_argument(
        "--source", "-s",
        choices=["coingecko", "coinmarketcap"],
        default="coingecko",
        help="API source to use (default: coingecko)"
    )
    
    parser.add_argument(
        "--api-key", "-k",
        help="API key for the selected source"
    )
    
    parser.add_argument(
        "--top", "-t",
        type=int,
        default=100,
        help="Number of top coins to collect (default: 100)"
    )
    
    parser.add_argument(
        "--coin", "-c",
        nargs="+",
        help="Specific coin(s) to collect (space-separated)"
    )
    
    parser.add_argument(
        "--format", "-f",
        choices=["json", "csv"],
        default="json",
        help="Output format (default: json)"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("data/processed"),
        help="Output directory (default: data/processed)"
    )
    
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("data/cache"),
        help="Cache directory (default: data/cache)"
    )
    
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable caching"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Get API key from args or environment
    api_key = args.api_key
    if not api_key and args.source == "coinmarketcap":
        api_key = os.getenv("CMC_API_KEY")
    elif not api_key and args.source == "coingecko":
        api_key = os.getenv("COINGECKO_API_KEY")
    
    # Initialize collector
    if args.verbose:
        print(f"Initializing {args.source} collector...")
    
    try:
        collector = MarketCollector(
            api_source=args.source,
            api_key=api_key,
            cache_dir=args.cache_dir,
            output_dir=args.output
        )
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    # Collect data
    if args.coin:
        # Collect specific coins
        coins = []
        for coin_id in args.coin:
            if args.verbose:
                print(f"Collecting data for {coin_id}...")
            try:
                coin_data = collector.collect_coin_data(
                    coin_id, 
                    use_cache=not args.no_cache
                )
                coins.append(coin_data)
                if args.verbose:
                    print(f"  {coin_data.name}: ${coin_data.current_price:,.2f}")
            except Exception as e:
                print(f"Error collecting {coin_id}: {e}")
        
        # Export
        if coins:
            from src.data.models import MarketData
            from datetime import datetime
            
            market_data = MarketData(
                timestamp=datetime.now(),
                total_market_cap=0,
                btc_dominance=0,
                coins=coins
            )
            output_path = collector.export_data(
                market_data, 
                format=args.format,
                prefix="selected_coins"
            )
            print(f"Exported to: {output_path}")
    
    else:
        # Collect market data
        if args.verbose:
            print(f"Collecting top {args.top} coins...")
        
        try:
            market_data = collector.collect_market_data(
                top_n=args.top,
                use_cache=not args.no_cache
            )
            
            if args.verbose:
                print(f"Total market cap: ${market_data.total_market_cap:,.0f}")
                print(f"BTC dominance: {market_data.btc_dominance:.1f}%")
                print(f"Coins collected: {len(market_data.coins)}")
            
            # Export
            output_path = collector.export_data(
                market_data,
                format=args.format,
                prefix="market_data"
            )
            print(f"Exported to: {output_path}")
            
        except Exception as e:
            print(f"Error collecting market data: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 测试脚本运行**

```bash
python scripts/data_collection/collect_market_data.py --help
```

Expected: Shows help message with usage examples

- [ ] **Step 3: 提交命令行脚本**

```bash
git add scripts/data_collection/collect_market_data.py
git commit -m "$(cat <<'EOF'
feat: 添加市场数据采集命令行工具

- 支持CoinGecko和CoinMarketCap数据源
- 支持采集市场整体数据或指定币种
- 支持JSON和CSV导出格式
- 支持缓存控制
- 完整的命令行参数和帮助文档

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: 更新模块导出和最终测试

**Files:**
- Modify: `src/data/__init__.py`
- Modify: `src/api/__init__.py`

- [ ] **Step 1: 更新模块导出**

修改 `src/data/__init__.py`：

```python
"""Data models, cache, and export utilities."""
from src.data.models import CoinData, MarketData
from src.data.cache import DataCache
from src.data.exporters import DataExporter

__all__ = ["CoinData", "MarketData", "DataCache", "DataExporter"]
```

修改 `src/api/__init__.py`：

```python
"""API clients for cryptocurrency data sources."""
from src.api.base import BaseAPIClient
from src.api.coingecko import CoinGeckoClient
from src.api.coinmarketcap import CoinMarketCapClient

__all__ = ["BaseAPIClient", "CoinGeckoClient", "CoinMarketCapClient"]
```

- [ ] **Step 2: 运行全部测试**

```bash
pytest tests/ -v --tb=short
```

Expected: PASS - All tests pass

- [ ] **Step 3: 提交最终更改**

```bash
git add src/data/__init__.py src/api/__init__.py
git commit -m "$(cat <<'EOF'
chore: 更新模块导出

- 导出所有公共类和函数
- 方便外部模块导入使用

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## 完成检查清单

- [ ] 所有测试通过：`pytest tests/ -v`
- [ ] 代码可以导入：`python -c "from src import data, api, collector"`
- [ ] CLI工具可用：`python scripts/data_collection/collect_market_data.py --help`
- [ ] 文档完整

---

## 使用示例

```bash
# 采集前100个币种数据（CoinGecko免费）
python scripts/data_collection/collect_market_data.py --source coingecko --top 100 -v

# 采集指定币种
python scripts/data_collection/collect_market_data.py --coin bitcoin ethereum solana

# 使用CoinMarketCap（需要API密钥）
python scripts/data_collection/collect_market_data.py --source coinmarketcap --api-key YOUR_KEY

# 导出为CSV格式
python scripts/data_collection/collect_market_data.py --format csv
```
