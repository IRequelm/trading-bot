import pandas as pd
from dataclasses import dataclass
from typing import Optional, Dict
from .tradingview_pivots import calculate_daily_pivot_levels

@dataclass
class PivotLevelsSignal:
    side: str
    confidence: float
    entry_level: Optional[str] = None
    exit_level: Optional[str] = None
    pivot: Optional[float] = None
    r1: Optional[float] = None
    r2: Optional[float] = None
    r3: Optional[float] = None
    r4: Optional[float] = None
    s1: Optional[float] = None
    s2: Optional[float] = None
    s3: Optional[float] = None
    s4: Optional[float] = None


def compute_pivot_levels_signals(df: pd.DataFrame, symbol: str = "", current_position: dict = None) -> PivotLevelsSignal:
    """
    Day-trading pivot strategy using Camarilla:
    - Buy at S3→R1, S2→R2, S1→R3 as price touches each support
    - Allow multiple positions simultaneously
    - Each position exits at its target resistance
    - Buy signals only when crossing INTO the support zone (not while staying in it)
    """
    if df.empty or len(df) < 50:
        return PivotLevelsSignal(side="hold", confidence=0.0)
    
    levels = calculate_daily_pivot_levels(df, symbol=symbol)
    if not levels:
        return PivotLevelsSignal(side="hold", confidence=0.0)
    
    pivot = levels['pivot']
    s1, s2, s3, s4 = levels['s1'], levels['s2'], levels['s3'], levels['s4']
    r1, r2, r3, r4 = levels['r1'], levels['r2'], levels['r3'], levels['r4']
    current_price = float(df.iloc[-1]['close'])
    threshold_pct = 0.005  # 0.5% threshold - tighter to catch bounce point
    
    # Get previous price to detect cross
    prev_price = float(df.iloc[-2]['close']) if len(df) > 1 else current_price
    
    # If we have a position, check for exit conditions
    if current_position and current_position.get('shares', 0) > 0:
        entry_level = current_position.get('entry_level', None)
        partial_done = current_position.get('partial_done', False)

        # S3 logic: partial at R1, final at R2
        if entry_level == 'S3':
            if not partial_done and current_price >= r1:
                return PivotLevelsSignal(side="sell", confidence=0.95, entry_level='S3', exit_level='R1', pivot=pivot, r1=r1, r2=r2, r3=r3, r4=r4, s1=s1, s2=s2, s3=s3, s4=s4)
            if current_price >= r2:
                return PivotLevelsSignal(side="sell", confidence=0.95, entry_level='S3', exit_level='R2', pivot=pivot, r1=r1, r2=r2, r3=r3, r4=r4, s1=s1, s2=s2, s3=s3, s4=s4)

        # S2 logic: full at R3
        if entry_level == 'S2' and current_price >= r3:
            return PivotLevelsSignal(side="sell", confidence=0.95, entry_level='S2', exit_level='R3', pivot=pivot, r1=r1, r2=r2, r3=r3, r4=r4, s1=s1, s2=s2, s3=s3, s4=s4)

        # Hold existing position
        return PivotLevelsSignal(side="hold", confidence=0.5, pivot=pivot, r1=r1, r2=r2, r3=r3, r4=r4, s1=s1, s2=s2, s3=s3, s4=s4)
    
    # No position - check for new entry opportunities
    # Only buy when price crosses INTO the support zone from above
    # Priority: S3 > S2 > S1 (most profitable trades first)
    
    # Buy at S3 (target R2) - detect cross into S3 zone
    if s3 and prev_price > s3 * (1 + threshold_pct) and current_price <= s3 * (1 + threshold_pct):
        return PivotLevelsSignal(side="buy", confidence=0.95, entry_level='S3', exit_level='R2', pivot=pivot, r1=r1, r2=r2, r3=r3, r4=r4, s1=s1, s2=s2, s3=s3, s4=s4)
    
    # Buy at S2 (target R3) - detect cross into S2 zone
    elif s2 and prev_price > s2 * (1 + threshold_pct) and current_price <= s2 * (1 + threshold_pct):
        return PivotLevelsSignal(side="buy", confidence=0.85, entry_level='S2', exit_level='R3', pivot=pivot, r1=r1, r2=r2, r3=r3, r4=r4, s1=s1, s2=s2, s3=s3, s4=s4)
    
    # No S1 entries (tighten to S2/S3 only)
    
    return PivotLevelsSignal(side="hold", confidence=0.3, pivot=pivot, r1=r1, r2=r2, r3=r3, r4=r4, s1=s1, s2=s2, s3=s3, s4=s4)
