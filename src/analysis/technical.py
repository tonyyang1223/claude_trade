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
        cache_key = f"ohlcv_{symbol.replace('/', '_')}_{timeframe}_{limit}"

        # Try cache first
        cached = self.cache.load(cache_key)
        if cached:
            df = pd.DataFrame(cached)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            return df

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
        - Price near MA50 (consolidation) -> 3
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