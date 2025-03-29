from backtester import Strategy, Backtest
from backtester.loaders import OptionQuoteLoader, IndexQuoteLoader, IndexOHLCLoader
from backtester.strategies import OptionPosition, Position
from loguru import logger
import pandas as pd
import ta
from decimal import Decimal

# Sell put spread when price crosses above SMA...
# Take profit or stop loss

class PutSpread(Strategy):
    def __init__(self, 
                 short_strike: int, 
                 spread_width: int, 
                 profit_pct: float, 
                 loss_pct: float,
                 min_credit: float = 0.10,  # $10 default
                 sma_period: int = 180,  # 3 minutes
                 rsi_period: int = 60,   # 1 minute
                 rsi_lower: float = 30,
                 rsi_upper: float = 70,
                 atr_period: int = 60,   # 1 minute
                 atr_threshold: float = 0.0005):  # 0.05% for 1s data
        super().__init__()
        self.sma_period = sma_period
        self.rsi_period = rsi_period
        self.rsi_lower = rsi_lower
        self.rsi_upper = rsi_upper
        self.atr_period = atr_period
        self.atr_threshold = atr_threshold
        self.short_strike = short_strike
        self.spread_width = spread_width
        self.profit_pct = profit_pct
        self.loss_pct = loss_pct
        self.min_credit = min_credit

    def prepare_indicators(self, index_quotes: pd.DataFrame, index_ohlc: pd.DataFrame) -> pd.DataFrame:
        index_quotes['sma'] = ta.trend.sma_indicator(index_quotes['price'], self.sma_period)
        index_quotes['rsi'] = ta.momentum.rsi(index_quotes['price'], window=self.rsi_period)
        index_quotes['atr'] = ta.volatility.average_true_range(
            index_ohlc['high'], index_ohlc['low'], index_ohlc['close'], 
            window=self.atr_period
        )
        index_quotes['atr_pct'] = index_quotes['atr'] / index_quotes['price']
        index_quotes['higher_low'] = index_ohlc['low'] > index_ohlc['low'].shift(1)
        return index_quotes

    def check_entry(self, index_quotes: pd.Series, chains: pd.DataFrame) -> Position | None:
        time = index_quotes.name
        price = index_quotes['price']
        
        # Skip if missing data
        if any(pd.isna(index_quotes[x]) for x in ['sma', 'rsi', 'atr_pct', 'higher_low']):
            return None
            
        # Entry conditions
        rsi_ok = self.rsi_lower < index_quotes['rsi'] < self.rsi_upper  # Not extreme
        volatility_ok = index_quotes['atr_pct'] < self.atr_threshold  # Not too volatile
        trend_ok = index_quotes['higher_low'] and price > index_quotes['sma']  # Uptrend
        
        if not all([rsi_ok, volatility_ok, trend_ok]):
            return None
            
        atm = round(price / 5) * 5
        sell_strike = atm - self.short_strike
        buy_strike = sell_strike - self.spread_width
        
        sell_data = chains.loc[(time, sell_strike)]
        buy_data = chains.loc[(time, buy_strike)]
        
        sell_bid = round(float(sell_data[('bid', False)]), 2)
        sell_mid = round(float(sell_data[('mid', False)]), 2)
        buy_bid = round(float(buy_data[('bid', False)]), 2)
        buy_mid = round(float(buy_data[('mid', False)]), 2)
        
        if not all(p > 0 for p in [sell_bid, sell_mid, buy_bid, buy_mid]):
            return None
            
        credit = sell_mid - buy_mid
        if credit < self.min_credit:
            return None
            
        return Position(
            entry_time=time,
            direction=-1,
            options=[
                OptionPosition(strike=sell_strike, right='P', entry_price=sell_bid, quantity=-1, entry_mid=sell_mid),
                OptionPosition(strike=buy_strike, right='P', entry_price=buy_bid, quantity=1, entry_mid=buy_mid)
            ]
        )

    def update_mids(self, chains: pd.DataFrame, time: pd.Timestamp) -> None:
        # Only log if debug level is enabled
        t = time.strftime('%Y-%m-%d %H:%M:%S') if logger.level('DEBUG').enabled else None
        for opt in self.options:
            strike_data = chains.loc[(time, opt.strike)]
            opt.exit_mid = float(strike_data.loc[strike_data['right'] == opt.right, 'mid'].iloc[0])
            
        if t:
            logger.trace(f"{t}: PnL: {self.pnl/self.entry_price():.2%}  \t\t${self.entry_price():.2f} -> ${self.current_price():.2f} = ${self.pnl:.2f}")

    def calculate_metrics(self, positions):
        if not positions:
            return {'mar': -999}  # Clear signal for no trades
        
        # Debug zero entry prices (shouldn't happen)
        for p in positions:
            if p.entry_price() == 0:
                logger.error(f"Found position with zero entry price: {p}")
            
        returns = pd.Series([p.pnl / abs(p.entry_price()) for p in positions])

# MAIN
if __name__ == "__main__":
    logger.info("Put Spread Backtest")
    strategy = PutSpread(
        short_strike=5,
        spread_width=5,
        profit_pct=0.5,
        loss_pct=-1.0
    )
    
    chains = OptionQuoteLoader('20250102', interval=1000).load()
    index_quotes = IndexQuoteLoader('20250102').load()
    index_ohlc = IndexOHLCLoader('20250102').load()
    
    index_quotes = strategy.prepare_indicators(index_quotes, index_ohlc)
    backtest = Backtest(chains, index_quotes, strategy)
    backtest.run()
    backtest.report() 
