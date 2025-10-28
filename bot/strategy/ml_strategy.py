import pandas as pd
import numpy as np
from dataclasses import dataclass
from sklearn.ensemble import RandomForestClassifier


@dataclass
class MLSignal:
    side: str  # 'buy', 'sell', 'hold'
    confidence: float


def calculate_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate various technical indicators for ML features"""
    df = df.copy()
    prices = df['close'].astype(float)
    
    # Simple Moving Averages
    df['sma_5'] = prices.rolling(window=5).mean()
    df['sma_10'] = prices.rolling(window=10).mean()
    df['sma_20'] = prices.rolling(window=20).mean()
    
    # Exponential Moving Averages
    df['ema_9'] = prices.ewm(span=9).mean()
    df['ema_21'] = prices.ewm(span=21).mean()
    
    # RSI
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # MACD
    ema_12 = prices.ewm(span=12).mean()
    ema_26 = prices.ewm(span=26).mean()
    df['macd'] = ema_12 - ema_26
    df['macd_signal'] = df['macd'].ewm(span=9).mean()
    
    # Bollinger Bands
    df['bb_mid'] = prices.rolling(window=20).mean()
    bb_std = prices.rolling(window=20).std()
    df['bb_upper'] = df['bb_mid'] + (bb_std * 2)
    df['bb_lower'] = df['bb_mid'] - (bb_std * 2)
    
    # ATR (Average True Range)
    high = df['high'].astype(float)
    low = df['low'].astype(float)
    tr1 = high - low
    tr2 = abs(high - prices.shift(1))
    tr3 = abs(low - prices.shift(1))
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['atr'] = true_range.rolling(window=14).mean()
    
    # Price change features
    df['price_change'] = prices.pct_change()
    df['price_change_5'] = prices.pct_change(5)
    df['price_change_10'] = prices.pct_change(10)
    
    # Volume features
    volume = df['volume'].astype(float)
    df['volume_ma'] = volume.rolling(window=20).mean()
    df['volume_ratio'] = volume / df['volume_ma']
    
    return df


def compute_ml_signals(df: pd.DataFrame) -> MLSignal:
    """
    ML-based strategy optimized for 5m charts
    Uses Random Forest to predict price movements
    """
    if df.empty or len(df) < 50:
        return MLSignal(side="hold", confidence=0.0)
    
    try:
        # Calculate features
        df_with_features = calculate_technical_indicators(df)
        
        # Drop NaN rows
        df_clean = df_with_features.dropna()
        
        if len(df_clean) < 30:
            return MLSignal(side="hold", confidence=0.0)
        
        # Prepare features
        feature_cols = ['sma_5', 'sma_10', 'sma_20', 'ema_9', 'ema_21', 'rsi', 
                       'macd', 'macd_signal', 'bb_mid', 'bb_upper', 'bb_lower',
                       'atr', 'price_change', 'price_change_5', 'price_change_10',
                       'volume_ratio']
        
        # Get recent data
        X = df_clean[feature_cols].values
        
        if len(X) < 30:
            return MLSignal(side="hold", confidence=0.0)
        
        # Create labels based on future price movements (for training)
        # For 5m charts, predict if price will go up in next 3-5 bars
        future_prices = df_clean['close'].shift(-3).bfill()  # Look 3 bars ahead
        price_change = (future_prices - df_clean['close']) / df_clean['close']
        
        # Labels: 1 for buy (price goes up 0.1% or more), 0 for sell/hold
        y = (price_change > 0.001).astype(int)  # More aggressive threshold
        
        # Use more data for training (last 100 samples)
        train_size = min(100, len(X) - 1)
        X_train = X[-train_size:]
        y_train = y[-train_size:]
        
        # Train Random Forest with more trees for better accuracy
        rf = RandomForestClassifier(
            n_estimators=50,  # More trees
            max_depth=8,      # Deeper trees
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=1
        )
        rf.fit(X_train, y_train)
        
        # Predict on most recent data
        X_current = X[-1:].reshape(1, -1)
        prediction = rf.predict(X_current)[0]
        probabilities = rf.predict_proba(X_current)[0]
        confidence = max(probabilities)
        
        # More aggressive: lower threshold to generate more trades
        # Convert to signal
        if prediction == 1 and confidence > 0.4:  # Lower from 0.5 to 0.4
            return MLSignal(side="buy", confidence=confidence)
        elif prediction == 0 and confidence > 0.4:  # Also generate sell signals
            return MLSignal(side="sell", confidence=confidence)
        else:
            return MLSignal(side="hold", confidence=0.3)
            
    except Exception as e:
        print(f"ML Strategy error: {e}")
        return MLSignal(side="hold", confidence=0.0)
