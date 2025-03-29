from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import pandas as pd
from loguru import logger

@dataclass
class OptionPosition:
    strike: float
    right: str  # 'C' or 'P'
    entry_price: float
    quantity: int
    entry_mid: float
    exit_mid: float | None = None
    
    @property
    def pnl(self) -> float:
        return (self.exit_mid - self.entry_price) * self.quantity if self.exit_mid else 0

@dataclass
class Position:
    entry_time: datetime
    direction: int
    options: list[OptionPosition]
    exit_time: Optional[datetime] = None
    
    @property
    def pnl(self) -> float:
        return sum(opt.pnl for opt in self.options)

    def __str__(self) -> str:
        return f"Entry: ${self.entry_price():.2f};  Current: ${self.current_price():.2f} | " + '; '.join(f"{opt.quantity}@{opt.strike}=${opt.entry_price}" for opt in self.options)
    
    def update_mids(self, chains: pd.DataFrame, time: datetime) -> None:
        """Update exit mids for PnL calculation"""
        t = time.strftime('%Y-%m-%d %H:%M:%S')
        for opt in self.options:
            is_call = opt.right == 'C'
            opt.exit_mid = chains.loc[(time, opt.strike), ('mid', is_call)]
            
        logger.debug(f"{t}: PnL: {self.pnl/self.entry_price():.2%}  \t\t${self.entry_price():.2f} -> ${self.current_price():.2f} = ${self.pnl:.2f}")

    def entry_price(self) -> float:
        return sum(opt.entry_price * opt.quantity for opt in self.options)

    def current_price(self) -> float:
        return sum(opt.exit_mid * opt.quantity for opt in self.options) if self.options and self.options[0].exit_mid else 0



class Strategy:
    def __init__(self, profit_pct: float = 0.5, loss_pct: float = -1.0):
        self.profit_pct = profit_pct  # Profit target
        self.loss_pct = loss_pct      # Stop loss
        
    def check_entry(self, index_quotes: pd.Series, chains: pd.DataFrame) -> Position | None:
        # Get current price and calculate strikes
        price = float(index_quotes['price'])
        atm = round(price / 5) * 5
        call_strike = atm + 5
        put_strike = atm - 5
        
        # Get option data
        try:
            call_data = chains.loc[(index_quotes.name, call_strike)]
            put_data = chains.loc[(index_quotes.name, put_strike)]
            
            # Access pivoted data directly
            call_bid = call_data[('bid', True)]
            call_mid = call_data[('mid', True)]
            put_bid = put_data[('bid', False)]
            put_mid = put_data[('mid', False)]
            
            if call_data.empty or put_data.empty:
                return None
                
            # Check for valid prices
            if not all(p > 0 for p in [call_bid, call_mid, put_bid, put_mid]):
                return None
                
            # Entry logic
            if call_mid > put_mid:
                return Position(
                    entry_time=index_quotes.name,
                    direction=1,
                    options=[
                        OptionPosition(strike=call_strike, right='C', entry_price=call_bid, quantity=1, entry_mid=call_mid),
                        OptionPosition(strike=put_strike, right='P', entry_price=put_bid, quantity=1, entry_mid=put_mid)
                    ]
                )
                
        except (KeyError, IndexError):
            return None
            
        return None
    
    def check_exit(self, position: Position, index_quotes: pd.Series) -> bool:
        """Default exit logic based on profit/loss targets. Assumes update_mids has been called this interval."""
        initial_value = abs(sum(opt.entry_price * opt.quantity for opt in position.options))
        pnl_pct = position.pnl / initial_value # assumes update_mids has been called this interval
        return pnl_pct >= self.profit_pct or pnl_pct <= self.loss_pct

