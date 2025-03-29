from datetime import datetime
import pandas as pd
from loguru import logger
from typing import Dict
import time



class OptionQuoteLoader:
    def __init__(self, date: str, interval: int = 1000, root: str = 'SPXW'):
        self.path = f"data/thetadata/v2/bulk_hist/option/quote/{root}/{interval}/{date}.csv.zst"
        self.date = date

    def load(self) -> pd.DataFrame:
        start = pd.Timestamp.now()
        
        # Load underlying to get reference price - first price is now valid
        underlying = IndexQuoteLoader(self.date).load()
        mid_price = underlying['price'].iloc[0]
        logger.debug(f"Reference price: {mid_price}")
        
        # Load all data first
        df = pd.read_csv(
            self.path, 
            compression='zstd',
            usecols=['date', 'ms_of_day', 'strike', 'bid', 'ask', 'right'],
            dtype={
                'strike': 'float32',
                'bid': 'float32',
                'ask': 'float32',
                'right': 'category'
            }
        )
        
        # Convert strikes to match index format
        df['strike'] = df['strike'] / 1000
        
        # Create datetime and mid price
        df['datetime'] = pd.to_datetime(df['date'].astype(str), format='%Y%m%d') + pd.to_timedelta(df['ms_of_day'], unit='ms')
        df['mid'] = (df['bid'] + df['ask']) / 2
        
        # Filter strikes within ±100 points of mid_price
        min_strike = mid_price - 200
        max_strike = mid_price + 200
        df = df[(df['strike'] >= min_strike) & (df['strike'] <= max_strike)]
        
        # Now pivot
        df['is_call'] = df['right'] == 'C'
        pivoted = df.pivot_table(
            index=['datetime', 'strike'],
            columns='is_call',
            values=['bid', 'ask', 'mid']
        )
        
        # Drop first row (9:30:00 with zero prices) to match underlying
        pivoted = pivoted.loc[pd.Timestamp(f"{self.date} 09:30:01"):]
        
        # Then validate intervals
        if not self._validate_intervals(pivoted):
            raise ValueError(f"Invalid intervals in options data for {self.date}")
        
        logger.debug(f"OptionQuote data loaded in {(pd.Timestamp.now() - start).total_seconds():.2f}s. Strikes {min_strike:.0f}-{max_strike:.0f}. {pivoted.shape}")
        logger.debug(f"DataFrame memory usage: {pivoted.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
        logger.debug(f"DataFrame info: {pivoted.info(memory_usage='deep')}")
        return pivoted

    def _validate_intervals(self, df: pd.DataFrame) -> bool:
        expected_idx = pd.date_range(
            f"{self.date} 09:30:01", 
            f"{self.date} 16:00:00", 
            freq='s'
        )
        
        # Get unique datetime values from MultiIndex
        actual_times = df.index.get_level_values('datetime').unique()
        logger.debug(f"Expected {len(expected_idx)} intervals, got {len(actual_times)}")
        
        if len(actual_times) != len(expected_idx):
            logger.error(f"Missing {len(expected_idx) - len(actual_times)} intervals in {self.date}")
            missing = expected_idx.difference(actual_times)
            if len(missing):
                logger.error(f"First missing: {missing[0]}, Last missing: {missing[-1]}")
            return False
        
        return True


class IndexQuoteLoader:
    def __init__(self, date: str, interval: int = 1000, root: str = 'SPX'):
        self.path = f"data/thetadata/v2/hist/index/price/{root}/{interval}/{date}.csv.zst"
        self.date = date
        
    def load(self) -> pd.DataFrame:
        start = pd.Timestamp.now()
        
        df = pd.read_csv(self.path, compression='zstd')
        df['datetime'] = pd.to_datetime(df['date'].astype(str), format='%Y%m%d') + pd.to_timedelta(df['ms_of_day'], unit='ms')
        result = df.set_index(['datetime'])
        
        # Drop first row (9:30:00 with zero prices)
        result = result.iloc[1:]
        
        # Validate data continuity
        if not self._validate_intervals(result):
            raise ValueError(f"Invalid intervals in underlying data for {self.date}")
        
        logger.debug(f"Underlying data loaded in {(pd.Timestamp.now() - start).total_seconds():.2f}s.  {result.shape}")
        return result

    def _validate_intervals(self, df: pd.DataFrame) -> bool:
        expected_idx = pd.date_range(
            f"{self.date} 09:30:01", 
            f"{self.date} 16:00:00",
            freq='s'
        )
        
        # Get unique datetime values from MultiIndex
        actual_times = df.index.get_level_values('datetime').unique()
        logger.debug(f"Expected {len(expected_idx)} intervals, got {len(actual_times)}")
        
        if len(actual_times) != len(expected_idx):
            logger.error(f"Missing {len(expected_idx) - len(actual_times)} intervals in {self.date}")
            missing = expected_idx.difference(actual_times)
            if len(missing):
                logger.error(f"First missing: {missing[0]}, Last missing: {missing[-1]}")
            return False
        
        return True


class IndexOHLCLoader:
    def __init__(self, date: str, interval: int = 1000, root: str = 'SPX'):
        self.path = f"data/thetadata/v2/hist/index/ohlc/{root}/{interval}/{date}.csv.zst"
        self.date = date
        
    def load(self) -> pd.DataFrame:
        start = pd.Timestamp.now()
        
        df = pd.read_csv(
            self.path, 
            compression='zstd',
            usecols=['date', 'ms_of_day', 'open', 'high', 'low', 'close']
        )
        
        df['datetime'] = pd.to_datetime(df['date'].astype(str), format='%Y%m%d') + pd.to_timedelta(df['ms_of_day'], unit='ms')
        result = df.set_index(['datetime'])
        
        # Drop first row (9:30:00 with zero prices)
        result = result.iloc[1:]
        
        # Validate data continuity
        if not self._validate_intervals(result):
            raise ValueError(f"Invalid intervals in underlying data for {self.date}")
        
        logger.debug(f"OHLC data loaded in {(pd.Timestamp.now() - start).total_seconds():.2f}s. {result.shape}")
        return result

    def _validate_intervals(self, df: pd.DataFrame) -> bool:
        # Reuse existing validation logic
        expected_idx = pd.date_range(
            f"{self.date} 09:30:01", 
            f"{self.date} 15:59:59", 
            freq='s'
        )
        actual_times = df.index
        return len(actual_times) == len(expected_idx)





