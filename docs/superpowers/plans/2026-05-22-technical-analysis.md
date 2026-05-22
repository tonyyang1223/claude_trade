# 技术指标分析模块实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现技术指标分析模块，支持RSI、移动平均线、支撑阻力位、趋势判断、斐波那契回撤、量价分析，输出TechnicalIndicators数据模型。

**Architecture:** 使用ccxt连接Binance获取K线数据，本地计算各项技术指标，通过评分规则转换为1-5分信号。模块化设计，每个指标独立函数，TechnicalAnalyzer类统一调度。

**Tech Stack:** Python 3.10+, ccxt, pandas, numpy, pandas-ta, pydantic, pytest

---

## 文件结构

```
src/
├── analysis/
│   ├── __init__.py
│   └── technical.py           # 技术指标分析主模块
├── data/
│   └── models.py              # 扩展TechnicalIndicators模型

tests/
└── test_technical.py          # 技术指标测试

scripts/
└── analysis/
    └── analyze_technical.py   # CLI入口
```

---

## Task 1: 扩展数据模型 - TechnicalIndicators

**Files:**
- Modify: `src/data/models.py`
- Modify: `src/data/__init__.py`
- Create: `tests/test_technical_models.py`

- [ ] **Step 1: 写失败的测试**

创建 `tests/test_technical_models.py`：

```python
"""Tests for TechnicalIndicators model."""
import pytest
from datetime import datetime
from src.data.models import TechnicalIndicators


class TestTechnicalIndicators:
    """Tests for TechnicalIndicators model."""

    def test_create_technical_indicators(self):
        """Test creating TechnicalIndicators instance."""
        indicators = TechnicalIndicators(
            rsi=55.5,
            rsi_signal=3,
            ma_50=65000.0,
            ma_200=58000.0,
            ma_signal=4,
            support_levels=[60000.0, 58000.0],
            resistance_levels=[70000.0, 75000.0],
            trend="up",
            trend_signal=4,
            fibonacci_levels={"38.2": 62000.0, "50.0": 60000.0, "61.8": 58000.0},
            volume_ratio=0.05,
            volume_signal=3,
            timestamp=datetime(2024, 1, 1, 12, 0, 0)
        )
        assert indicators.rsi == 55.5
        assert indicators.rsi_signal == 3
        assert indicators.trend == "up"
        assert len(indicators.support_levels) == 2

    def test_rsi_signal_range(self):
        """Test RSI signal is in valid range."""
        indicators = TechnicalIndicators(
            rsi=50.0,
            rsi_signal=5,
            ma_50=100.0,
            ma_200=90.0,
            ma_signal=3,
            support_levels=[],
            resistance_levels=[],
            trend="sideways",
            trend_signal=3,
            fibonacci_levels={},
            volume_ratio=0.1,
            volume_signal=3
        )
        assert 1 <= indicators.rsi_signal <= 5

    def test_trend_valid_values(self):
        """Test trend is valid value."""
        for trend in ["up", "down", "sideways"]:
            indicators = TechnicalIndicators(
                rsi=50.0,
                rsi_signal=3,
                ma_50=100.0,
                ma_200=90.0,
                ma_signal=3,
                support_levels=[],
                resistance_levels=[],
                trend=trend,
                trend_signal=3,
                fibonacci_levels={},
                volume_ratio=0.1,
                volume_signal=3
            )
            assert indicators.trend == trend
```

- [ ] **Step 2: 运行测试验证失败**

Run: `python -m pytest tests/test_technical_models.py -v`
Expected: FAIL - ImportError: cannot import name 'TechnicalIndicators'

- [ ] **Step 3: 实现TechnicalIndicators模型**

在 `src/data/models.py` 末尾添加：

```python
class TechnicalIndicators(BaseModel):
    """Technical indicators data for a cryptocurrency.
    
    Attributes:
        rsi: RSI value (0-100)
        rsi_signal: RSI signal score (1-5)
        ma_50: 50-day moving average
        ma_200: 200-day moving average
        ma_signal: Moving average signal (1-5)
        support_levels: List of support price levels
        resistance_levels: List of resistance price levels
        trend: Trend direction (up/down/sideways)
        trend_signal: Trend signal (1-5)
        fibonacci_levels: Fibonacci retracement levels
        volume_ratio: Volume/Market cap ratio
        volume_signal: Volume signal (1-5)
        timestamp: When data was calculated
    """
    rsi: float
    rsi_signal: int = Field(ge=1, le=5)
    ma_50: float
    ma_200: float
    ma_signal: int = Field(ge=1, le=5)
    support_levels: List[float]
    resistance_levels: List[float]
    trend: str
    trend_signal: int = Field(ge=1, le=5)
    fibonacci_levels: Dict[str, float]
    volume_ratio: float
    volume_signal: int = Field(ge=1, le=5)
    timestamp: datetime = Field(default_factory=datetime.now)
```

需要在文件顶部添加 `Dict` 导入：
```python
from typing import Optional, List, Dict
```

- [ ] **Step 4: 更新模块导出**

修改 `src/data/__init__.py`：

```python
"""Data models, cache, and export utilities."""
from src.data.models import CoinData, MarketData, TechnicalIndicators
from src.data.cache import DataCache
from src.data.exporters import DataExporter

__all__ = ["CoinData", "MarketData", "TechnicalIndicators", "DataCache", "DataExporter"]
```

- [ ] **Step 5: 运行测试验证通过**

Run: `python -m pytest tests/test_technical_models.py -v`
Expected: PASS - All tests pass

- [ ] **Step 6: 提交**

```bash
git add src/data/models.py src/data/__init__.py tests/test_technical_models.py
git commit -m "feat: 添加TechnicalIndicators数据模型

- RSI指标及信号评分
- 移动平均线及信号
- 支撑阻力位列表
- 趋势判断及信号
- 斐波那契回撤位
- 量价关系分析

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 2: 创建analysis模块结构

**Files:**
- Create: `src/analysis/__init__.py`
- Create: `src/analysis/technical.py` (空文件框架)

- [ ] **Step 1: 创建analysis包**

创建 `src/analysis/__init__.py`：

```python
"""Analysis modules for cryptocurrency evaluation."""
from src.analysis.technical import TechnicalAnalyzer

__all__ = ["TechnicalAnalyzer"]
```

- [ ] **Step 2: 创建technical.py框架**

创建 `src/analysis/technical.py`：

```python
"""Technical analysis module for cryptocurrency indicators."""
import ccxt
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from src.data.models import TechnicalIndicators
from src.data.cache import DataCache


class TechnicalAnalyzer:
    """Analyzes technical indicators for cryptocurrencies.
    
    Uses ccxt to fetch OHLCV data from Binance (free, no API key needed).
    
    Attributes:
        exchange: ccxt exchange instance
        cache: DataCache for caching OHLCV data
        
    Example:
        >>> analyzer = TechnicalAnalyzer()
        >>> indicators = analyzer.analyze("BTC/USDT", days=200)
    """
    
    def __init__(self, cache_dir: Path = Path("data/cache")):
        """Initialize technical analyzer.
        
        Args:
            cache_dir: Directory for caching OHLCV data
        """
        self.exchange = ccxt.binance()
        self.cache = DataCache(cache_dir, expire_hours=1)
    
    def fetch_ohlcv(self, symbol: str, timeframe: str = "1d", limit: int = 200) -> pd.DataFrame:
        """Fetch OHLCV data from exchange.
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            timeframe: Timeframe ('1d', '1h', etc.)
            limit: Number of candles to fetch
            
        Returns:
            DataFrame with OHLCV data
        """
        raise NotImplementedError
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calculate RSI indicator.
        
        Args:
            prices: Series of closing prices
            period: RSI period (default 14)
            
        Returns:
            RSI value (0-100)
        """
        raise NotImplementedError
    
    def score_rsi(self, rsi: float) -> int:
        """Score RSI value.
        
        Args:
            rsi: RSI value (0-100)
            
        Returns:
            Score (1-5)
        """
        raise NotImplementedError
    
    def calculate_ma(self, prices: pd.Series, period: int) -> float:
        """Calculate moving average.
        
        Args:
            prices: Series of closing prices
            period: MA period
            
        Returns:
            MA value
        """
        raise NotImplementedError
    
    def score_ma(self, current_price: float, ma_50: float, ma_200: float) -> int:
        """Score based on MA relationship.
        
        Args:
            current_price: Current price
            ma_50: 50-day MA
            ma_200: 200-day MA
            
        Returns:
            Score (1-5)
        """
        raise NotImplementedError
    
    def identify_support_resistance(self, df: pd.DataFrame, window: int = 20) -> tuple:
        """Identify support and resistance levels.
        
        Args:
            df: DataFrame with OHLCV data
            window: Window for local extrema detection
            
        Returns:
            Tuple of (support_levels, resistance_levels)
        """
        raise NotImplementedError
    
    def determine_trend(self, current_price: float, ma_50: float, ma_200: float) -> tuple:
        """Determine trend direction.
        
        Args:
            current_price: Current price
            ma_50: 50-day MA
            ma_200: 200-day MA
            
        Returns:
            Tuple of (trend, trend_signal)
        """
        raise NotImplementedError
    
    def calculate_fibonacci(self, high: float, low: float) -> Dict[str, float]:
        """Calculate Fibonacci retracement levels.
        
        Args:
            high: Swing high price
            low: Swing low price
            
        Returns:
            Dict with Fibonacci levels
        """
        raise NotImplementedError
    
    def calculate_volume_ratio(self, volume: float, market_cap: float) -> float:
        """Calculate volume/market cap ratio.
        
        Args:
            volume: 24h trading volume
            market_cap: Market capitalization
            
        Returns:
            Volume ratio
        """
        raise NotImplementedError
    
    def score_volume(self, volume_ratio: float) -> int:
        """Score volume ratio.
        
        Args:
            volume_ratio: Volume/market cap ratio
            
        Returns:
            Score (1-5)
        """
        raise NotImplementedError
    
    def analyze(self, symbol: str, days: int = 200, market_cap: Optional[float] = None) -> TechnicalIndicators:
        """Perform full technical analysis.
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            days: Number of days to analyze
            market_cap: Optional market cap for volume ratio
            
        Returns:
            TechnicalIndicators instance
        """
        raise NotImplementedError
```

- [ ] **Step 3: 提交框架**

```bash
git add src/analysis/__init__.py src/analysis/technical.py
git commit -m "feat: 添加技术分析模块框架

- TechnicalAnalyzer类框架
- 各指标计算方法占位

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 3: 实现RSI计算和评分

**Files:**
- Modify: `src/analysis/technical.py`
- Create: `tests/test_technical.py`

- [ ] **Step 1: 写失败的测试**

创建 `tests/test_technical.py`：

```python
"""Tests for technical analysis module."""
import pytest
import pandas as pd
import numpy as np
from src.analysis.technical import TechnicalAnalyzer


class TestRSI:
    """Tests for RSI calculation and scoring."""

    def test_calculate_rsi_normal(self):
        """Test RSI calculation with normal data."""
        # Create sample price data (uptrend)
        prices = pd.Series([100, 101, 102, 103, 104, 105, 106, 107, 108, 109,
                           110, 111, 112, 113, 114, 115, 116, 117, 118, 119])
        analyzer = TechnicalAnalyzer()
        rsi = analyzer.calculate_rsi(prices, period=14)
        # Uptrend should have RSI > 50
        assert rsi > 50
        assert 0 <= rsi <= 100

    def test_calculate_rsi_downtrend(self):
        """Test RSI calculation with downtrend."""
        # Create sample price data (downtrend)
        prices = pd.Series([119, 118, 117, 116, 115, 114, 113, 112, 111, 110,
                           109, 108, 107, 106, 105, 104, 103, 102, 101, 100])
        analyzer = TechnicalAnalyzer()
        rsi = analyzer.calculate_rsi(prices, period=14)
        # Downtrend should have RSI < 50
        assert rsi < 50
        assert 0 <= rsi <= 100

    def test_score_rsi_oversold(self):
        """Test RSI scoring for oversold condition."""
        analyzer = TechnicalAnalyzer()
        assert analyzer.score_rsi(25) == 5  # Oversold, buy signal
        assert analyzer.score_rsi(15) == 5

    def test_score_rsi_overbought(self):
        """Test RSI scoring for overbought condition."""
        analyzer = TechnicalAnalyzer()
        assert analyzer.score_rsi(75) == 1  # Overbought, caution
        assert analyzer.score_rsi(85) == 1

    def test_score_rsi_neutral(self):
        """Test RSI scoring for neutral condition."""
        analyzer = TechnicalAnalyzer()
        assert analyzer.score_rsi(50) == 3  # Neutral
        assert analyzer.score_rsi(45) == 3
        assert analyzer.score_rsi(55) == 3
```

- [ ] **Step 2: 运行测试验证失败**

Run: `python -m pytest tests/test_technical.py::TestRSI -v`
Expected: FAIL - NotImplementedError

- [ ] **Step 3: 实现RSI计算和评分**

在 `src/analysis/technical.py` 中实现方法：

```python
def calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
    """Calculate RSI indicator.
    
    Args:
        prices: Series of closing prices
        period: RSI period (default 14)
        
    Returns:
        RSI value (0-100)
    """
    if len(prices) < period + 1:
        raise ValueError(f"Need at least {period + 1} prices for RSI calculation")
    
    # Calculate price changes
    delta = prices.diff()
    
    # Separate gains and losses
    gains = delta.where(delta > 0, 0)
    losses = (-delta).where(delta < 0, 0)
    
    # Calculate average gains and losses using EMA
    avg_gain = gains.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = losses.ewm(com=period - 1, min_periods=period).mean()
    
    # Calculate RS and RSI
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return float(rsi.iloc[-1])


def score_rsi(self, rsi: float) -> int:
    """Score RSI value.
    
    Scoring rules:
    - < 30: Oversold (buy signal) -> 5
    - 30-40: Weak -> 4
    - 40-60: Neutral -> 3
    - 60-70: Strong -> 2
    - >= 70: Overbought (caution) -> 1
    
    Args:
        rsi: RSI value (0-100)
        
    Returns:
        Score (1-5)
    """
    if rsi < 30:
        return 5  # Oversold, buy opportunity
    elif rsi < 40:
        return 4
    elif rsi <= 60:
        return 3  # Neutral
    elif rsi <= 70:
        return 2
    else:
        return 1  # Overbought, caution
```

- [ ] **Step 4: 运行测试验证通过**

Run: `python -m pytest tests/test_technical.py::TestRSI -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/analysis/technical.py tests/test_technical.py
git commit -m "feat: 实现RSI计算和评分

- calculate_rsi: 使用EMA计算RSI
- score_rsi: 5级评分规则

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 4: 实现移动平均线计算和评分

**Files:**
- Modify: `src/analysis/technical.py`
- Modify: `tests/test_technical.py`

- [ ] **Step 1: 写失败的测试**

在 `tests/test_technical.py` 添加：

```python
class TestMovingAverage:
    """Tests for moving average calculation and scoring."""

    def test_calculate_ma(self):
        """Test MA calculation."""
        prices = pd.Series([100, 101, 102, 103, 104, 105, 106, 107, 108, 109])
        analyzer = TechnicalAnalyzer()
        ma = analyzer.calculate_ma(prices, period=5)
        # MA of last 5: (105+106+107+108+109)/5 = 107
        assert ma == pytest.approx(107.0)

    def test_score_ma_golden_cross(self):
        """Test MA scoring with golden cross (price > MA50 > MA200)."""
        analyzer = TechnicalAnalyzer()
        # Price above both MAs, bullish
        score = analyzer.score_ma(current_price=70000, ma_50=65000, ma_200=58000)
        assert score >= 4

    def test_score_ma_death_cross(self):
        """Test MA scoring with death cross (price < MA50 < MA200)."""
        analyzer = TechnicalAnalyzer()
        # Price below both MAs, bearish
        score = analyzer.score_ma(current_price=50000, ma_50=55000, ma_200=60000)
        assert score <= 2

    def test_score_ma_between(self):
        """Test MA scoring when price between MAs."""
        analyzer = TechnicalAnalyzer()
        # Price between MAs
        score = analyzer.score_ma(current_price=62000, ma_50=65000, ma_200=58000)
        assert 2 <= score <= 4
```

- [ ] **Step 2: 运行测试验证失败**

Run: `python -m pytest tests/test_technical.py::TestMovingAverage -v`
Expected: FAIL - NotImplementedError

- [ ] **Step 3: 实现MA计算和评分**

在 `src/analysis/technical.py` 中实现：

```python
def calculate_ma(self, prices: pd.Series, period: int) -> float:
    """Calculate moving average.
    
    Args:
        prices: Series of closing prices
        period: MA period
        
    Returns:
        MA value
    """
    if len(prices) < period:
        raise ValueError(f"Need at least {period} prices for MA calculation")
    return float(prices.iloc[-period:].mean())


def score_ma(self, current_price: float, ma_50: float, ma_200: float) -> int:
    """Score based on MA relationship.
    
    Scoring rules:
    - Price > MA50 > MA200 (golden cross, strong uptrend) -> 5
    - Price > MA50 but MA50 < MA200 (potential reversal) -> 4
    - Price around MA50 (consolidation) -> 3
    - Price < MA50 but MA50 > MA200 (potential reversal down) -> 2
    - Price < MA50 < MA200 (death cross, downtrend) -> 1
    
    Args:
        current_price: Current price
        ma_50: 50-day MA
        ma_200: 200-day MA
        
    Returns:
        Score (1-5)
    """
    # Golden cross pattern
    if current_price > ma_50 > ma_200:
        return 5
    # Price above 50 MA but 50 MA below 200 MA (early uptrend)
    elif current_price > ma_50 and ma_50 < ma_200:
        return 4
    # Price near 50 MA (within 5%)
    elif abs(current_price - ma_50) / ma_50 < 0.05:
        return 3
    # Price below 50 MA but 50 MA above 200 MA (early downtrend)
    elif current_price < ma_50 and ma_50 > ma_200:
        return 2
    # Death cross pattern
    else:
        return 1
```

- [ ] **Step 4: 运行测试验证通过**

Run: `python -m pytest tests/test_technical.py::TestMovingAverage -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/analysis/technical.py tests/test_technical.py
git commit -m "feat: 实现移动平均线计算和评分

- calculate_ma: 简单移动平均计算
- score_ma: 金叉/死叉评分规则

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 5: 实现支撑阻力位识别

**Files:**
- Modify: `src/analysis/technical.py`
- Modify: `tests/test_technical.py`

- [ ] **Step 1: 写失败的测试**

在 `tests/test_technical.py` 添加：

```python
class TestSupportResistance:
    """Tests for support and resistance identification."""

    def test_identify_support_resistance(self):
        """Test support/resistance identification."""
        # Create price data with clear support and resistance
        data = {
            'high': [105, 110, 108, 115, 112, 118, 116, 120, 118, 122],
            'low': [95, 100, 98, 105, 102, 108, 106, 112, 110, 115],
            'close': [100, 105, 103, 110, 107, 113, 111, 116, 114, 118]
        }
        df = pd.DataFrame(data)
        analyzer = TechnicalAnalyzer()
        support, resistance = analyzer.identify_support_resistance(df, window=3)
        
        assert isinstance(support, list)
        assert isinstance(resistance, list)
        # Support levels should be lower than resistance
        if support and resistance:
            assert min(support) < max(resistance)

    def test_identify_support_resistance_empty(self):
        """Test with insufficient data."""
        df = pd.DataFrame({'high': [100], 'low': [90], 'close': [95]})
        analyzer = TechnicalAnalyzer()
        support, resistance = analyzer.identify_support_resistance(df, window=3)
        assert support == []
        assert resistance == []
```

- [ ] **Step 2: 运行测试验证失败**

Run: `python -m pytest tests/test_technical.py::TestSupportResistance -v`
Expected: FAIL - NotImplementedError

- [ ] **Step 3: 实现支撑阻力识别**

在 `src/analysis/technical.py` 中实现：

```python
def identify_support_resistance(self, df: pd.DataFrame, window: int = 20) -> tuple:
    """Identify support and resistance levels.
    
    Uses local minima for support and local maxima for resistance.
    
    Args:
        df: DataFrame with 'high', 'low', 'close' columns
        window: Window for local extrema detection
        
    Returns:
        Tuple of (support_levels, resistance_levels)
    """
    if len(df) < window * 2:
        return [], []
    
    support_levels = []
    resistance_levels = []
    
    lows = df['low'].values
    highs = df['high'].values
    
    # Find local minima (support)
    for i in range(window, len(lows) - window):
        if all(lows[i] <= lows[i-j] for j in range(1, window + 1)) and \
           all(lows[i] <= lows[i+j] for j in range(1, window + 1)):
            support_levels.append(float(lows[i]))
    
    # Find local maxima (resistance)
    for i in range(window, len(highs) - window):
        if all(highs[i] >= highs[i-j] for j in range(1, window + 1)) and \
           all(highs[i] >= highs[i+j] for j in range(1, window + 1)):
            resistance_levels.append(float(highs[i]))
    
    # Keep only recent and significant levels
    # Sort and keep top 3 most recent
    support_levels = sorted(set(support_levels))[-3:] if support_levels else []
    resistance_levels = sorted(set(resistance_levels))[-3:] if resistance_levels else []
    
    return support_levels, resistance_levels
```

- [ ] **Step 4: 运行测试验证通过**

Run: `python -m pytest tests/test_technical.py::TestSupportResistance -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/analysis/technical.py tests/test_technical.py
git commit -m "feat: 实现支撑阻力位识别

- identify_support_resistance: 局部极值算法
- 返回最近3个支撑位和阻力位

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 6: 实现趋势判断和斐波那契回撤

**Files:**
- Modify: `src/analysis/technical.py`
- Modify: `tests/test_technical.py`

- [ ] **Step 1: 写失败的测试**

在 `tests/test_technical.py` 添加：

```python
class TestTrendAndFibonacci:
    """Tests for trend determination and Fibonacci levels."""

    def test_determine_trend_uptrend(self):
        """Test uptrend detection."""
        analyzer = TechnicalAnalyzer()
        # Price above both MAs
        trend, signal = analyzer.determine_trend(70000, 65000, 58000)
        assert trend == "up"
        assert signal >= 4

    def test_determine_trend_downtrend(self):
        """Test downtrend detection."""
        analyzer = TechnicalAnalyzer()
        # Price below both MAs
        trend, signal = analyzer.determine_trend(50000, 55000, 60000)
        assert trend == "down"
        assert signal <= 2

    def test_determine_trend_sideways(self):
        """Test sideways detection."""
        analyzer = TechnicalAnalyzer()
        # Price near MAs
        trend, signal = analyzer.determine_trend(65000, 64000, 62000)
        assert trend in ["up", "sideways"]

    def test_calculate_fibonacci(self):
        """Test Fibonacci retracement calculation."""
        analyzer = TechnicalAnalyzer()
        levels = analyzer.calculate_fibonacci(high=70000, low=50000)
        
        assert "23.6" in levels
        assert "38.2" in levels
        assert "50.0" in levels
        assert "61.8" in levels
        assert "78.6" in levels
        
        # Verify levels are between high and low
        for level_name, level_value in levels.items():
            assert low <= level_value <= high

    def test_fibonacci_values(self):
        """Test Fibonacci level values are correct."""
        analyzer = TechnicalAnalyzer()
        high, low = 70000, 50000
        diff = high - low
        levels = analyzer.calculate_fibonacci(high, low)
        
        assert levels["50.0"] == pytest.approx(low + diff * 0.5)
        assert levels["38.2"] == pytest.approx(low + diff * 0.382)
        assert levels["61.8"] == pytest.approx(low + diff * 0.618)
```

- [ ] **Step 2: 运行测试验证失败**

Run: `python -m pytest tests/test_technical.py::TestTrendAndFibonacci -v`
Expected: FAIL - NotImplementedError

- [ ] **Step 3: 实现趋势判断和斐波那契**

在 `src/analysis/technical.py` 中实现：

```python
def determine_trend(self, current_price: float, ma_50: float, ma_200: float) -> tuple:
    """Determine trend direction.
    
    Args:
        current_price: Current price
        ma_50: 50-day MA
        ma_200: 200-day MA
        
    Returns:
        Tuple of (trend, trend_signal)
    """
    # Calculate price position relative to MAs
    price_vs_ma50 = (current_price - ma_50) / ma_50
    price_vs_ma200 = (current_price - ma_200) / ma_200
    ma50_vs_ma200 = (ma_50 - ma_200) / ma_200
    
    # Strong uptrend: price well above both MAs, MA50 > MA200
    if price_vs_ma50 > 0.05 and price_vs_ma200 > 0.1 and ma50_vs_ma200 > 0:
        return "up", 5
    # Moderate uptrend
    elif price_vs_ma50 > 0 and price_vs_ma200 > 0:
        return "up", 4
    # Sideways: price near MAs
    elif abs(price_vs_ma50) < 0.05:
        return "sideways", 3
    # Moderate downtrend
    elif price_vs_ma50 < 0 and price_vs_ma200 < 0:
        return "down", 2
    # Strong downtrend
    else:
        return "down", 1


def calculate_fibonacci(self, high: float, low: float) -> Dict[str, float]:
    """Calculate Fibonacci retracement levels.
    
    Args:
        high: Swing high price
        low: Swing low price
        
    Returns:
        Dict with Fibonacci levels (23.6%, 38.2%, 50%, 61.8%, 78.6%)
    """
    diff = high - low
    
    return {
        "23.6": low + diff * 0.236,
        "38.2": low + diff * 0.382,
        "50.0": low + diff * 0.5,
        "61.8": low + diff * 0.618,
        "78.6": low + diff * 0.786
    }
```

- [ ] **Step 4: 运行测试验证通过**

Run: `python -m pytest tests/test_technical.py::TestTrendAndFibonacci -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/analysis/technical.py tests/test_technical.py
git commit -m "feat: 实现趋势判断和斐波那契回撤

- determine_trend: 基于MA关系判断趋势
- calculate_fibonacci: 计算5个关键回撤位

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 7: 实现量价分析和OHLCV数据获取

**Files:**
- Modify: `src/analysis/technical.py`
- Modify: `tests/test_technical.py`

- [ ] **Step 1: 写失败的测试**

在 `tests/test_technical.py` 添加：

```python
class TestVolumeAnalysis:
    """Tests for volume analysis."""

    def test_calculate_volume_ratio(self):
        """Test volume ratio calculation."""
        analyzer = TechnicalAnalyzer()
        ratio = analyzer.calculate_volume_ratio(volume=50000000000, market_cap=1000000000000)
        assert ratio == 0.05

    def test_score_volume_high(self):
        """Test volume scoring with high volume."""
        analyzer = TechnicalAnalyzer()
        # High volume ratio indicates strong interest
        score = analyzer.score_volume(0.15)
        assert score >= 4

    def test_score_volume_low(self):
        """Test volume scoring with low volume."""
        analyzer = TechnicalAnalyzer()
        # Low volume ratio
        score = analyzer.score_volume(0.01)
        assert score <= 2

    def test_score_volume_normal(self):
        """Test volume scoring with normal volume."""
        analyzer = TechnicalAnalyzer()
        score = analyzer.score_volume(0.05)
        assert 2 <= score <= 4
```

- [ ] **Step 2: 运行测试验证失败**

Run: `python -m pytest tests/test_technical.py::TestVolumeAnalysis -v`
Expected: FAIL - NotImplementedError

- [ ] **Step 3: 实现量价分析**

在 `src/analysis/technical.py` 中实现：

```python
def calculate_volume_ratio(self, volume: float, market_cap: float) -> float:
    """Calculate volume/market cap ratio.
    
    Args:
        volume: 24h trading volume
        market_cap: Market capitalization
        
    Returns:
        Volume ratio
    """
    if market_cap <= 0:
        raise ValueError("Market cap must be positive")
    return volume / market_cap


def score_volume(self, volume_ratio: float) -> int:
    """Score volume ratio.
    
    Higher volume ratio indicates more liquidity and interest.
    
    Scoring rules:
    - > 0.15: Very high volume -> 5
    - 0.10-0.15: High volume -> 4
    - 0.05-0.10: Normal volume -> 3
    - 0.02-0.05: Low volume -> 2
    - < 0.02: Very low volume -> 1
    
    Args:
        volume_ratio: Volume/market cap ratio
        
    Returns:
        Score (1-5)
    """
    if volume_ratio > 0.15:
        return 5
    elif volume_ratio > 0.10:
        return 4
    elif volume_ratio > 0.05:
        return 3
    elif volume_ratio > 0.02:
        return 2
    else:
        return 1
```

- [ ] **Step 4: 实现OHLCV数据获取**

在 `src/analysis/technical.py` 中实现：

```python
def fetch_ohlcv(self, symbol: str, timeframe: str = "1d", limit: int = 200) -> pd.DataFrame:
    """Fetch OHLCV data from exchange.
    
    Args:
        symbol: Trading pair (e.g., 'BTC/USDT')
        timeframe: Timeframe ('1d', '1h', etc.)
        limit: Number of candles to fetch
        
    Returns:
        DataFrame with OHLCV data (timestamp, open, high, low, close, volume)
    """
    cache_key = f"ohlcv_{symbol}_{timeframe}_{limit}"
    
    # Try cache first
    cached = self.cache.load(cache_key)
    if cached:
        return pd.DataFrame(cached)
    
    # Fetch from exchange
    ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    
    df = pd.DataFrame(
        ohlcv,
        columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
    )
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    # Cache the result
    self.cache.save(cache_key, df.to_dict('records'))
    
    return df
```

- [ ] **Step 5: 运行测试验证通过**

Run: `python -m pytest tests/test_technical.py::TestVolumeAnalysis -v`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add src/analysis/technical.py tests/test_technical.py
git commit -m "feat: 实现量价分析和OHLCV获取

- calculate_volume_ratio: 交易量/市值比率
- score_volume: 量价评分规则
- fetch_ohlcv: ccxt获取K线数据

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 8: 实现完整分析流程

**Files:**
- Modify: `src/analysis/technical.py`
- Modify: `tests/test_technical.py`

- [ ] **Step 1: 写失败的测试**

在 `tests/test_technical.py` 添加：

```python
class TestFullAnalysis:
    """Tests for full technical analysis."""

    def test_analyze_with_mock_data(self):
        """Test full analysis with mock OHLCV data."""
        analyzer = TechnicalAnalyzer()
        
        # Mock the fetch_ohlcv method
        mock_df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=200, freq='D'),
            'open': [50000 + i * 10 for i in range(200)],
            'high': [50500 + i * 10 for i in range(200)],
            'low': [49500 + i * 10 for i in range(200)],
            'close': [50000 + i * 10 for i in range(200)],
            'volume': [1000000] * 200
        })
        
        analyzer.fetch_ohlcv = lambda *args, **kwargs: mock_df
        
        result = analyzer.analyze("BTC/USDT", days=200, market_cap=1000000000000)
        
        assert isinstance(result, TechnicalIndicators)
        assert 0 <= result.rsi <= 100
        assert 1 <= result.rsi_signal <= 5
        assert result.trend in ["up", "down", "sideways"]
        assert len(result.fibonacci_levels) == 5

    def test_analyze_returns_valid_indicators(self):
        """Test that analyze returns valid TechnicalIndicators."""
        analyzer = TechnicalAnalyzer()
        
        mock_df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=200, freq='D'),
            'open': [100] * 200,
            'high': [105] * 200,
            'low': [95] * 200,
            'close': [100] * 200,
            'volume': [1000000] * 200
        })
        
        analyzer.fetch_ohlcv = lambda *args, **kwargs: mock_df
        
        result = analyzer.analyze("TEST/USDT", days=200)
        
        assert result.ma_50 is not None
        assert result.ma_200 is not None
        assert isinstance(result.support_levels, list)
        assert isinstance(result.resistance_levels, list)
```

- [ ] **Step 2: 运行测试验证失败**

Run: `python -m pytest tests/test_technical.py::TestFullAnalysis -v`
Expected: FAIL - NotImplementedError

- [ ] **Step 3: 实现完整分析流程**

在 `src/analysis/technical.py` 中实现：

```python
def analyze(self, symbol: str, days: int = 200, market_cap: Optional[float] = None) -> TechnicalIndicators:
    """Perform full technical analysis.
    
    Args:
        symbol: Trading pair (e.g., 'BTC/USDT')
        days: Number of days to analyze
        market_cap: Optional market cap for volume ratio
        
    Returns:
        TechnicalIndicators instance
    """
    # Fetch OHLCV data
    df = self.fetch_ohlcv(symbol, timeframe="1d", limit=days)
    
    if len(df) < 50:
        raise ValueError(f"Insufficient data: need at least 50 candles, got {len(df)}")
    
    prices = df['close']
    current_price = float(prices.iloc[-1])
    
    # Calculate RSI
    rsi = self.calculate_rsi(prices)
    rsi_signal = self.score_rsi(rsi)
    
    # Calculate MAs
    ma_50 = self.calculate_ma(prices, 50)
    ma_200 = self.calculate_ma(prices, min(200, len(prices)))
    ma_signal = self.score_ma(current_price, ma_50, ma_200)
    
    # Identify support and resistance
    support_levels, resistance_levels = self.identify_support_resistance(df)
    
    # Determine trend
    trend, trend_signal = self.determine_trend(current_price, ma_50, ma_200)
    
    # Calculate Fibonacci levels (use recent high/low)
    recent_high = float(df['high'].iloc[-50:].max())
    recent_low = float(df['low'].iloc[-50:].min())
    fibonacci_levels = self.calculate_fibonacci(recent_high, recent_low)
    
    # Calculate volume ratio
    volume = float(df['volume'].iloc[-1])
    if market_cap and market_cap > 0:
        volume_ratio = self.calculate_volume_ratio(volume, market_cap)
    else:
        # Estimate volume ratio from average
        avg_volume = float(df['volume'].mean())
        volume_ratio = volume / (avg_volume * 10) if avg_volume > 0 else 0.05
    
    volume_signal = self.score_volume(volume_ratio)
    
    return TechnicalIndicators(
        rsi=rsi,
        rsi_signal=rsi_signal,
        ma_50=ma_50,
        ma_200=ma_200,
        ma_signal=ma_signal,
        support_levels=support_levels,
        resistance_levels=resistance_levels,
        trend=trend,
        trend_signal=trend_signal,
        fibonacci_levels=fibonacci_levels,
        volume_ratio=volume_ratio,
        volume_signal=volume_signal
    )
```

- [ ] **Step 4: 运行测试验证通过**

Run: `python -m pytest tests/test_technical.py::TestFullAnalysis -v`
Expected: PASS

- [ ] **Step 5: 运行所有测试**

Run: `python -m pytest tests/test_technical.py -v`
Expected: PASS - All tests pass

- [ ] **Step 6: 提交**

```bash
git add src/analysis/technical.py tests/test_technical.py
git commit -m "feat: 实现完整技术分析流程

- analyze方法整合所有指标计算
- 支持自定义分析天数
- 支持可选市值参数

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 9: 创建CLI命令行工具

**Files:**
- Create: `scripts/analysis/analyze_technical.py`

- [ ] **Step 1: 创建CLI脚本**

创建 `scripts/analysis/analyze_technical.py`：

```python
#!/usr/bin/env python3
"""Command-line interface for technical analysis.

Usage:
    python scripts/analysis/analyze_technical.py --symbol BTC/USDT --days 200
    python scripts/analysis/analyze_technical.py --symbol ETH/USDT --market-cap 400000000000
"""
import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.analysis.technical import TechnicalAnalyzer


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Perform technical analysis on a cryptocurrency",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --symbol BTC/USDT --days 200
  %(prog)s --symbol ETH/USDT --market-cap 400000000000
  %(prog)s --symbol SOL/USDT --output json
        """
    )
    
    parser.add_argument(
        "--symbol", "-s",
        required=True,
        help="Trading pair (e.g., BTC/USDT)"
    )
    
    parser.add_argument(
        "--days", "-d",
        type=int,
        default=200,
        help="Number of days to analyze (default: 200)"
    )
    
    parser.add_argument(
        "--market-cap", "-m",
        type=float,
        help="Market cap for volume ratio calculation"
    )
    
    parser.add_argument(
        "--output", "-o",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)"
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
    
    if args.verbose:
        print(f"Analyzing {args.symbol} with {args.days} days of data...")
    
    try:
        analyzer = TechnicalAnalyzer()
        result = analyzer.analyze(
            symbol=args.symbol,
            days=args.days,
            market_cap=args.market_cap
        )
        
        if args.output == "json":
            import json
            print(json.dumps(result.model_dump(), indent=2, default=str))
        else:
            print(f"\n{'='*50}")
            print(f"Technical Analysis: {args.symbol}")
            print(f"{'='*50}")
            print(f"\nRSI: {result.rsi:.2f} (Signal: {result.rsi_signal}/5)")
            print(f"50-day MA: ${result.ma_50:,.2f}")
            print(f"200-day MA: ${result.ma_200:,.2f}")
            print(f"MA Signal: {result.ma_signal}/5")
            print(f"\nTrend: {result.trend.upper()} (Signal: {result.trend_signal}/5)")
            print(f"\nSupport Levels: {[f'${x:,.2f}' for x in result.support_levels]}")
            print(f"Resistance Levels: {[f'${x:,.2f}' for x in result.resistance_levels]}")
            print(f"\nFibonacci Levels:")
            for level, value in result.fibonacci_levels.items():
                print(f"  {level}%: ${value:,.2f}")
            print(f"\nVolume Ratio: {result.volume_ratio:.4f} (Signal: {result.volume_signal}/5)")
            print(f"\nTimestamp: {result.timestamp}")
            print(f"{'='*50}\n")
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 测试CLI帮助**

Run: `python scripts/analysis/analyze_technical.py --help`
Expected: Shows help message

- [ ] **Step 3: 提交CLI**

```bash
git add scripts/analysis/analyze_technical.py
git commit -m "feat: 添加技术分析CLI工具

- 支持指定交易对和分析天数
- 支持可选市值参数
- 支持text/json输出格式

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 10: 更新依赖和最终测试

**Files:**
- Modify: `requirements.txt`
- Modify: `src/analysis/__init__.py`

- [ ] **Step 1: 确认依赖已存在**

检查 `requirements.txt` 中是否已包含：
- ccxt>=4.0.0
- pandas>=2.0.0
- numpy>=1.24.0
- pydantic>=2.0.0
- pytest>=7.4.0

如已存在则无需修改。

- [ ] **Step 2: 运行完整测试套件**

Run: `python -m pytest tests/test_technical.py tests/test_technical_models.py -v`
Expected: PASS - All tests pass

- [ ] **Step 3: 最终提交**

```bash
git add -A
git commit -m "chore: 完成技术指标分析模块

- TechnicalIndicators数据模型
- TechnicalAnalyzer分析器
- RSI/MA/支撑阻力/趋势/斐波那契/量价分析
- CLI命令行工具
- 完整测试覆盖

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## 完成检查清单

- [ ] 所有测试通过：`python -m pytest tests/test_technical*.py -v`
- [ ] 代码可以导入：`python -c "from src.analysis import TechnicalAnalyzer"`
- [ ] CLI工具可用：`python scripts/analysis/analyze_technical.py --help`
- [ ] 文档完整

---

## 使用示例

```bash
# 分析BTC
python scripts/analysis/analyze_technical.py --symbol BTC/USDT --days 200

# 分析ETH并指定市值
python scripts/analysis/analyze_technical.py --symbol ETH/USDT --market-cap 400000000000

# JSON格式输出
python scripts/analysis/analyze_technical.py --symbol SOL/USDT --output json
```