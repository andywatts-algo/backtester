from backtester import Strategy, OptionQuoteLoader, IndexQuoteLoader, Backtest
from loguru import logger
import pandas as pd
from backtester.strategies import OptionPosition, Position
import ta

# Sell put spread when price crosses above SMA...
# Take profit or stop loss

class SimpleStrategy(Strategy):
    def __init__(self):
        super().__init__()
        self.sma_period = 20
        self.profit_pct = 0.03  # 1% profit target
        self.loss_pct = -0.2   # 1% stop loss

    def prepare_indicators(self, underlying: pd.DataFrame) -> pd.DataFrame:
        underlying['sma'] = ta.trend.sma_indicator(underlying['price'], self.sma_period)
        return underlying

    def check_entry(self, underlying: pd.Series, chain: pd.DataFrame) -> Position | None:
        time = underlying.name
        
        # Skip if no price or price not above SMA
        if not (price := underlying['price']): return None
        if not price > underlying['sma']: return None
        
        # Round to nearest 5 points for strikes (e.g. 5900.00 -> 5900.0)
        call_strike = 5 * round((price + 5) / 5)
        put_strike = 5 * round((price - 5) / 5)
        
        try:
            # Get data for these strikes
            call = chain[chain.index.get_level_values('strike') == call_strike]
            put = chain[chain.index.get_level_values('strike') == put_strike]
            
            if call.empty or put.empty:
                logger.debug(f"{time}: Skip entry - missing strikes {call_strike}/{put_strike}")
                return None
                
            # Get prices
            call_bid = float(call['bid'].iloc[0])
            call_mid = float(call['mid'].iloc[0])
            put_bid = float(put['bid'].iloc[0])
            put_mid = float(put['mid'].iloc[0])
            
            logger.debug(f"{time}: Option prices - call={call_mid}, put={put_mid}")
            
            # Check for valid prices
            if not all(p > 0 for p in [call_bid, call_mid, put_bid, put_mid]):
                logger.debug(f"{time}: Skip entry - invalid prices: call={call_mid}, put={put_mid}")
                return None
                
            return Position(
                entry_time=underlying.name,
                direction=-1,
                options=[
                    OptionPosition(strike=call_strike, entry_price=call_bid, quantity=-1, entry_mid=call_mid),
                    OptionPosition(strike=put_strike, entry_price=put_bid, quantity=-1, entry_mid=put_mid)
                ]
            )
        except Exception as e:
            logger.debug(f"Error in check_entry: {e}")
            return None

# MAIN
if __name__ == "__main__":
    logger.info("Starting SimpleStrategy backtest")
    strategy = SimpleStrategy()

    cutoff_time = pd.Timestamp('2025-01-02 09:32:00') # First 2 mins only
    logger.info(f"Cutoff time: {cutoff_time}")
    
    chains = OptionQuoteLoader('20250102', interval=1000).load()
    chains = chains[chains.index.get_level_values('datetime') < cutoff_time]
    
    underlying = IndexQuoteLoader('20250102').load()  # 1-second intervals
    underlying = underlying[underlying.index < cutoff_time]
    
    underlying = strategy.prepare_indicators(underlying)   # Technical indicators
    logger.info(f"Testing on {len(chains)} rows from {chains.index[0]} to {chains.index[-1]}")

    backtest = Backtest(chains, underlying, strategy)
    backtest.run()
    backtest.report() 
