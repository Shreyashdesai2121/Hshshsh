"""
Analysis engine for technical analysis and signal generation.
Implements channel detection, KST indicator, and trading signal logic.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from scipy import stats
from loguru import logger

from models import Channel, KSTSignal, TradeSignal, SignalType, ChannelDetectionParams, KSTParams
from utils import calculate_fibonacci_levels


class AnalysisEngine:
    """Analysis engine for technical analysis and signal generation."""
    
    def __init__(self):
        self.channel_params = ChannelDetectionParams()
        self.kst_params = KSTParams()
    
    def detect_parallel_channel(self, df: pd.DataFrame) -> Channel:
        """
        Detect parallel channels using algorithmic approach.
        
        Algorithm:
        1. Find local peaks and troughs using rolling windows
        2. Fit linear regression lines to upper and lower points
        3. Validate channel based on touches and duration
        4. Return channel object with validation results
        """
        try:
            if len(df) < 50:  # Need sufficient data
                return Channel(
                    start_ts=datetime.now(),
                    end_ts=datetime.now(),
                    upper_line={"slope": 0, "intercept": 0},
                    lower_line={"slope": 0, "intercept": 0},
                    touches_upper=0,
                    touches_lower=0,
                    is_upward=False,
                    valid=False
                )
            
            # Find local peaks and troughs
            peaks, troughs = self._find_peaks_troughs(df)
            
            if len(peaks) < 2 or len(troughs) < 2:
                return Channel(
                    start_ts=datetime.now(),
                    end_ts=datetime.now(),
                    upper_line={"slope": 0, "intercept": 0},
                    lower_line={"slope": 0, "intercept": 0},
                    touches_upper=0,
                    touches_lower=0,
                    is_upward=False,
                    valid=False
                )
            
            # Fit lines to peaks and troughs
            upper_line, upper_points = self._fit_line_to_points(peaks)
            lower_line, lower_points = self._fit_line_to_points(troughs)
            
            # Calculate touches
            touches_upper = self._count_touches(df, upper_line, upper_points)
            touches_lower = self._count_touches(df, lower_line, lower_points)
            
            # Determine if channel is upward or downward
            is_upward = upper_line["slope"] > lower_line["slope"]
            
            # Calculate channel duration
            start_ts = df.index[0]
            end_ts = df.index[-1]
            duration_days = (end_ts - start_ts).days
            
            # Validate channel
            valid = (
                touches_upper >= self.channel_params.min_touches and
                touches_lower >= self.channel_params.min_touches and
                duration_days >= self.channel_params.min_days
            )
            
            # Calculate confidence based on touches and duration
            confidence = min(1.0, (touches_upper + touches_lower) / 10.0)
            
            channel = Channel(
                start_ts=start_ts,
                end_ts=end_ts,
                upper_line=upper_line,
                lower_line=lower_line,
                touches_upper=touches_upper,
                touches_lower=touches_lower,
                is_upward=is_upward,
                valid=valid,
                confidence=confidence,
                upper_points=upper_points,
                lower_points=lower_points
            )
            
            logger.debug(f"Channel detected: valid={valid}, touches_upper={touches_upper}, touches_lower={touches_lower}")
            return channel
        
        except Exception as e:
            logger.error(f"Error detecting channel: {e}")
            return Channel(
                start_ts=datetime.now(),
                end_ts=datetime.now(),
                upper_line={"slope": 0, "intercept": 0},
                lower_line={"slope": 0, "intercept": 0},
                touches_upper=0,
                touches_lower=0,
                is_upward=False,
                valid=False
            )
    
    def _find_peaks_troughs(self, df: pd.DataFrame, window: int = 5) -> Tuple[List[Tuple[datetime, float]], List[Tuple[datetime, float]]]:
        """Find local peaks and troughs in price data."""
        peaks = []
        troughs = []
        
        for i in range(window, len(df) - window):
            current_high = df.iloc[i]['high']
            current_low = df.iloc[i]['low']
            
            # Check if current high is a local peak
            if all(current_high >= df.iloc[i-j]['high'] for j in range(1, window+1)) and \
               all(current_high >= df.iloc[i+j]['high'] for j in range(1, window+1)):
                peaks.append((df.index[i], current_high))
            
            # Check if current low is a local trough
            if all(current_low <= df.iloc[i-j]['low'] for j in range(1, window+1)) and \
               all(current_low <= df.iloc[i+j]['low'] for j in range(1, window+1)):
                troughs.append((df.index[i], current_low))
        
        return peaks, troughs
    
    def _fit_line_to_points(self, points: List[Tuple[datetime, float]]) -> Tuple[Dict[str, float], List[Tuple[datetime, float]]]:
        """Fit a linear regression line to points."""
        if len(points) < 2:
            return {"slope": 0, "intercept": 0}, points
        
        # Convert timestamps to numeric values for regression
        x_values = np.array([(p[0] - points[0][0]).total_seconds() / 3600 for p in points])  # Hours since first point
        y_values = np.array([p[1] for p in points])
        
        # Fit linear regression
        slope, intercept, r_value, p_value, std_err = stats.linregress(x_values, y_values)
        
        return {"slope": slope, "intercept": intercept}, points
    
    def _count_touches(self, df: pd.DataFrame, line: Dict[str, float], line_points: List[Tuple[datetime, float]]) -> int:
        """Count how many times the price touches the line."""
        touches = 0
        tolerance = 0.01  # 1% tolerance
        
        for timestamp, row in df.iterrows():
            # Calculate expected price at this timestamp
            hours_since_start = (timestamp - line_points[0][0]).total_seconds() / 3600
            expected_price = line["slope"] * hours_since_start + line["intercept"]
            
            # Check if high or low is close to the line
            if abs(row['high'] - expected_price) / expected_price <= tolerance:
                touches += 1
            elif abs(row['low'] - expected_price) / expected_price <= tolerance:
                touches += 1
        
        return touches
    
    def compute_kst(self, df: pd.DataFrame) -> KSTSignal:
        """
        Compute No-Sure-Thing (KST) indicator.
        
        KST = (ROC1 * SMA1) + (ROC2 * SMA2) + (ROC3 * SMA3) + (ROC4 * SMA4)
        Signal = SMA of KST
        """
        try:
            if len(df) < max(self.kst_params.roc4, self.kst_params.sma4) + 10:
                return KSTSignal(
                    kst_value=0,
                    kst_signal=0,
                    crossover_direction="none",
                    timestamp=datetime.now()
                )
            
            # Calculate Rate of Change (ROC)
            roc1 = df['close'].pct_change(self.kst_params.roc1) * 100
            roc2 = df['close'].pct_change(self.kst_params.roc2) * 100
            roc3 = df['close'].pct_change(self.kst_params.roc3) * 100
            roc4 = df['close'].pct_change(self.kst_params.roc4) * 100
            
            # Calculate smoothed ROC
            sma1 = roc1.rolling(window=self.kst_params.sma1).mean()
            sma2 = roc2.rolling(window=self.kst_params.sma2).mean()
            sma3 = roc3.rolling(window=self.kst_params.sma3).mean()
            sma4 = roc4.rolling(window=self.kst_params.sma4).mean()
            
            # Calculate KST
            kst = (sma1 * 1) + (sma2 * 2) + (sma3 * 3) + (sma4 * 4)
            
            # Calculate signal line
            kst_signal = kst.rolling(window=self.kst_params.signal_period).mean()
            
            # Get latest values
            latest_kst = kst.iloc[-1] if not pd.isna(kst.iloc[-1]) else 0
            latest_signal = kst_signal.iloc[-1] if not pd.isna(kst_signal.iloc[-1]) else 0
            
            # Determine crossover direction
            if len(kst) >= 2 and len(kst_signal) >= 2:
                prev_kst = kst.iloc[-2]
                prev_signal = kst_signal.iloc[-2]
                
                if latest_kst > latest_signal and prev_kst <= prev_signal:
                    crossover_direction = "bullish"
                elif latest_kst < latest_signal and prev_kst >= prev_signal:
                    crossover_direction = "bearish"
                else:
                    crossover_direction = "none"
            else:
                crossover_direction = "none"
            
            # Calculate confidence based on signal strength
            confidence = min(1.0, abs(latest_kst - latest_signal) / 10.0)
            
            return KSTSignal(
                kst_value=latest_kst,
                kst_signal=latest_signal,
                crossover_direction=crossover_direction,
                timestamp=datetime.now(),
                confidence=confidence
            )
        
        except Exception as e:
            logger.error(f"Error computing KST: {e}")
            return KSTSignal(
                kst_value=0,
                kst_signal=0,
                crossover_direction="none",
                timestamp=datetime.now()
            )
    
    def check_breakout_20m(self, df: pd.DataFrame, channel: Channel) -> Optional[str]:
        """Check for breakout in 20-minute timeframe."""
        try:
            if not channel.valid or len(df) < 2:
                return None
            
            # Get last candle
            last_candle = df.iloc[-1]
            last_close = last_candle['close']
            
            # Calculate expected channel levels at last timestamp
            hours_since_start = (df.index[-1] - channel.start_ts).total_seconds() / 3600
            upper_level = channel.upper_line["slope"] * hours_since_start + channel.upper_line["intercept"]
            lower_level = channel.lower_line["slope"] * hours_since_start + channel.lower_line["intercept"]
            
            # Check for breakout
            if last_close > upper_level:
                return "breakout_up"
            elif last_close < lower_level:
                return "breakout_down"
            else:
                return None
        
        except Exception as e:
            logger.error(f"Error checking breakout: {e}")
            return None
    
    def compute_fibonacci_levels(self, channel: Channel) -> Dict[str, float]:
        """Compute Fibonacci retracement levels for channel."""
        try:
            if not channel.valid:
                return {}
            
            # Get channel high and low
            if channel.is_upward:
                high = channel.upper_line["intercept"] + channel.upper_line["slope"] * (
                    (channel.end_ts - channel.start_ts).total_seconds() / 3600
                )
                low = channel.lower_line["intercept"]
            else:
                high = channel.upper_line["intercept"]
                low = channel.lower_line["intercept"] + channel.lower_line["slope"] * (
                    (channel.end_ts - channel.start_ts).total_seconds() / 3600
                )
            
            # Calculate Fibonacci levels
            fib_levels = calculate_fibonacci_levels(high, low)
            
            return fib_levels
        
        except Exception as e:
            logger.error(f"Error computing Fibonacci levels: {e}")
            return {}
    
    def generate_trade_signal(
        self, 
        call_df_20m: pd.DataFrame, 
        call_df_2h: pd.DataFrame, 
        put_df_20m: pd.DataFrame, 
        put_df_2h: pd.DataFrame
    ) -> Optional[TradeSignal]:
        """
        Generate trading signal based on channel detection and KST confirmation.
        
        Strategy Logic:
        1. Detect channels in both call and put 20-minute data
        2. Compute KST signals in both call and put 2-hour data
        3. Check for opposite conditions (call channel up + call KST bullish AND put channel down + put KST bearish)
        4. Wait for breakout in the expected direction
        5. Generate entry signal
        """
        try:
            # Detect channels
            call_channel = self.detect_parallel_channel(call_df_20m)
            put_channel = self.detect_parallel_channel(put_df_20m)
            
            # Compute KST signals
            call_kst = self.compute_kst(call_df_2h)
            put_kst = self.compute_kst(put_df_2h)
            
            # Check if both channels are valid
            if not call_channel.valid or not put_channel.valid:
                logger.debug("Channels not valid for signal generation")
                return None
            
            # Check for opposite conditions
            call_condition = (
                call_channel.is_upward and 
                call_kst.crossover_direction == "bullish"
            )
            
            put_condition = (
                not put_channel.is_upward and 
                put_kst.crossover_direction == "bearish"
            )
            
            if not (call_condition and put_condition):
                logger.debug("KST conditions not met for signal generation")
                return None
            
            # Check for breakouts
            call_breakout = self.check_breakout_20m(call_df_20m, call_channel)
            put_breakout = self.check_breakout_20m(put_df_20m, put_channel)
            
            # Determine signal type based on breakouts
            signal_type = None
            instrument = ""
            strike = 0
            option_type = ""
            entry_price = 0.0
            
            if call_breakout == "breakout_up" and put_breakout == "breakout_down":
                # Buy call option
                signal_type = SignalType.BUY_CALL
                instrument = f"NIFTY{call_df_20m.index[-1].strftime('%d%b%y').upper()}"
                strike = int(call_df_20m.index[-1])  # Placeholder
                option_type = "CE"
                entry_price = call_df_20m.iloc[-1]['close']
            elif call_breakout == "breakout_down" and put_breakout == "breakout_up":
                # Buy put option
                signal_type = SignalType.BUY_PUT
                instrument = f"NIFTY{put_df_20m.index[-1].strftime('%d%b%y').upper()}"
                strike = int(put_df_20m.index[-1])  # Placeholder
                option_type = "PE"
                entry_price = put_df_20m.iloc[-1]['close']
            else:
                logger.debug("No valid breakout detected")
                return None
            
            # Calculate targets and stop loss
            target_price = None
            stop_loss_price = None
            
            if signal_type == SignalType.BUY_CALL:
                fib_levels = self.compute_fibonacci_levels(call_channel)
                if fib_levels:
                    # Use 0.236 or 0.5 based on profit potential
                    target_236 = fib_levels.get("0.236", 0)
                    target_50 = fib_levels.get("0.5", 0)
                    
                    profit_236 = (target_236 - entry_price) / entry_price * 100
                    if profit_236 >= 50:  # 50% profit threshold
                        target_price = target_236
                    else:
                        target_price = target_50
                
                # Stop loss at channel lower line
                hours_since_start = (call_df_20m.index[-1] - call_channel.start_ts).total_seconds() / 3600
                stop_loss_price = call_channel.lower_line["slope"] * hours_since_start + call_channel.lower_line["intercept"]
            
            elif signal_type == SignalType.BUY_PUT:
                fib_levels = self.compute_fibonacci_levels(put_channel)
                if fib_levels:
                    # Use 0.236 or 0.5 based on profit potential
                    target_236 = fib_levels.get("0.236", 0)
                    target_50 = fib_levels.get("0.5", 0)
                    
                    profit_236 = (target_236 - entry_price) / entry_price * 100
                    if profit_236 >= 50:  # 50% profit threshold
                        target_price = target_236
                    else:
                        target_price = target_50
                
                # Stop loss at channel upper line
                hours_since_start = (put_df_20m.index[-1] - put_channel.start_ts).total_seconds() / 3600
                stop_loss_price = put_channel.upper_line["slope"] * hours_since_start + put_channel.upper_line["intercept"]
            
            # Calculate confidence
            confidence = (call_channel.confidence + put_channel.confidence + 
                        call_kst.confidence + put_kst.confidence) / 4
            
            # Generate signal
            signal = TradeSignal(
                signal_type=signal_type,
                instrument=instrument,
                strike=strike,
                option_type=option_type,
                entry_price=entry_price,
                target_price=target_price,
                stop_loss_price=stop_loss_price,
                quantity=1,  # TODO: Make configurable
                reason=f"Channel breakout: Call {call_breakout}, Put {put_breakout}",
                confidence=confidence,
                channel_data=call_channel if signal_type == SignalType.BUY_CALL else put_channel,
                kst_data=call_kst if signal_type == SignalType.BUY_CALL else put_kst
            )
            
            logger.info(f"Generated signal: {signal_type.value} {instrument} at {entry_price}")
            return signal
        
        except Exception as e:
            logger.error(f"Error generating trade signal: {e}")
            return None
    
    def calculate_position_pnl(
        self, 
        entry_price: float, 
        current_price: float, 
        quantity: int, 
        side: str
    ) -> float:
        """Calculate position PnL."""
        try:
            if side.lower() == "long":
                return (current_price - entry_price) * quantity
            else:  # short
                return (entry_price - current_price) * quantity
        except Exception as e:
            logger.error(f"Error calculating PnL: {e}")
            return 0.0
    
    async def analyze_patterns(self, data_20min: pd.DataFrame, data_2hr: pd.DataFrame, symbol: str) -> Dict:
        """
        Analyze patterns for live monitoring.
        Returns pattern detection results for a single symbol.
        """
        try:
            if data_20min is None or data_2hr is None or len(data_20min) < 10 or len(data_2hr) < 10:
                return {"pattern_detected": False, "reason": "Insufficient data"}
            
            # Detect channel in 20-minute data
            channel = self.detect_parallel_channel(data_20min)
            
            if not channel.valid:
                return {"pattern_detected": False, "reason": "No valid channel detected"}
            
            # Compute KST in 2-hour data
            kst = self.compute_kst(data_2hr)
            
            if not kst.crossover_detected:
                return {"pattern_detected": False, "reason": "No KST crossover detected"}
            
            # Check for pattern conditions
            pattern_detected = False
            pattern_type = "Channel Breakout + KST"
            strength = 0.0
            kst_overlap = False
            breakout_confirmed = False
            channel_breakout_price = 0.0
            
            # Check if channel and KST conditions are met
            if channel.is_upward and kst.crossover_direction == "bullish":
                pattern_detected = True
                strength = 0.8
                kst_overlap = True
                
                # Check for breakout (last candle close above upper channel)
                if len(data_20min) > 0:
                    last_close = data_20min['close'].iloc[-1]
                    hours_since_start = (datetime.now() - channel.start_ts).total_seconds() / 3600
                    upper_level = channel.upper_line["slope"] * hours_since_start + channel.upper_line["intercept"]
                    
                    if last_close > upper_level:
                        breakout_confirmed = True
                        channel_breakout_price = last_close
                        strength = 0.9
            
            elif not channel.is_upward and kst.crossover_direction == "bearish":
                pattern_detected = True
                strength = 0.8
                kst_overlap = True
                
                # Check for breakout (last candle close below lower channel)
                if len(data_20min) > 0:
                    last_close = data_20min['close'].iloc[-1]
                    hours_since_start = (datetime.now() - channel.start_ts).total_seconds() / 3600
                    lower_level = channel.lower_line["slope"] * hours_since_start + channel.lower_line["intercept"]
                    
                    if last_close < lower_level:
                        breakout_confirmed = True
                        channel_breakout_price = last_close
                        strength = 0.9
            
            return {
                "pattern_detected": pattern_detected,
                "pattern_type": pattern_type,
                "strength": strength,
                "kst_overlap": kst_overlap,
                "breakout_confirmed": breakout_confirmed,
                "channel_breakout_price": channel_breakout_price,
                "channel": channel,
                "kst": kst
            }
            
        except Exception as e:
            logger.error(f"Error analyzing patterns for {symbol}: {e}")
            return {"pattern_detected": False, "reason": f"Analysis error: {str(e)}"}

    def should_exit_position(
        self, 
        position: Dict[str, Any], 
        current_price: float, 
        channel: Channel
    ) -> Tuple[bool, str]:
        """Check if position should be exited based on stop loss or target."""
        try:
            entry_price = position.get("entry_price", 0)
            target_price = position.get("target_price", 0)
            stop_loss_price = position.get("stop_loss_price", 0)
            side = position.get("side", "long")
            
            # Check target
            if target_price > 0:
                if side.lower() == "long" and current_price >= target_price:
                    return True, "target_hit"
                elif side.lower() == "short" and current_price <= target_price:
                    return True, "target_hit"
            
            # Check stop loss
            if stop_loss_price > 0:
                if side.lower() == "long" and current_price <= stop_loss_price:
                    return True, "stop_loss"
                elif side.lower() == "short" and current_price >= stop_loss_price:
                    return True, "stop_loss"
            
            # Check channel re-entry (stop loss condition)
            if channel and channel.valid:
                hours_since_start = (datetime.now() - channel.start_ts).total_seconds() / 3600
                upper_level = channel.upper_line["slope"] * hours_since_start + channel.upper_line["intercept"]
                lower_level = channel.lower_line["slope"] * hours_since_start + channel.lower_line["intercept"]
                
                if lower_level <= current_price <= upper_level:
                    return True, "channel_reentry"
            
            return False, ""
        
        except Exception as e:
            logger.error(f"Error checking exit conditions: {e}")
            return False, "error"


# Global analysis engine instance
analysis_engine = AnalysisEngine()