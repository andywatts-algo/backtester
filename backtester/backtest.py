from typing import Dict
from loguru import logger
from backtester.strategies import Strategy, Position
import pandas as pd
from datetime import datetime
import numpy as np

class Backtest:
    def __init__(self, chains, underlying, strategy: Strategy):
        self.chains = chains
        self.underlying = underlying
        self.strategy = strategy
        self.positions: list[Position] = []
        self.current_position: Position | None = None
        
    def _validate_interval(self, time: pd.Timestamp, index: pd.Series, chains: pd.DataFrame) -> bool:
        price = float(index['price'])
        if not price > 0:
            logger.trace(f"{time}: Skip - no price")
            return False
            
        atm = round(price / 5) * 5
        try:
            atm_data = chains.loc[(time, atm)]
            if not (atm_data[('mid', True)] > 0 and atm_data[('mid', False)] > 0):
                logger.trace(f"{time}: Skip - no valid ATM options at strike {atm}")
                return False
            return True
        except (KeyError, IndexError):
            logger.trace(f"{time}: Skip - KeyError/IndexError")
            return False
        
    def run(self) -> Dict:
        self.start_time = datetime.now()
        for time, index in self.underlying.iterrows():
            if not self._validate_interval(time, index, self.chains):
                continue

            if self.current_position:
                self.current_position.update_mids(self.chains, time)
                
                if self.strategy.check_exit(self.current_position, index):
                    self.current_position.exit_time = time
                    self.positions.append(self.current_position)
                    outcome = "WINNER" if self.current_position.pnl > 0 else "LOSER"
                    logger.debug(f"{time}: {outcome} closed with PnL: ${self.current_position.pnl:.2f}")
                    self.current_position = None
                
            if not self.current_position:
                if position := self.strategy.check_entry(index, self.chains):
                    self.current_position = position
                    logger.debug(f"{time}: NEW {position}")
        
        # Close any open position at end of backtest
        if self.current_position:
            last_time = self.underlying.index[-1]
            self.current_position.update_mids(self.chains, last_time)
            self.current_position.exit_time = last_time
            self.positions.append(self.current_position)
            outcome = "WINNER" if self.current_position.pnl > 0 else "LOSER"
            logger.debug(f"{last_time}: EOD {outcome} closed with PnL: ${self.current_position.pnl:.2f}")
        
        self.end_time = datetime.now()
        return self._calculate_metrics()
    

    def _calculate_metrics(self) -> Dict:
        if not self.positions:
            return {
                'total_pnl': 0, 
                'win_rate': 0, 
                'num_positions': 0, 
                'mar': 0, 
                'sortino': 0, 
                'return': 0,
                'profit_factor': 0
            }
            
        total_pnl = sum(p.pnl for p in self.positions)
        wins = sum(1 for p in self.positions if p.pnl > 0)
        
        # Calculate returns per trade
        returns = pd.Series([p.pnl / abs(p.entry_price()) for p in self.positions])
        
        # Calculate drawdown on trade returns
        cumulative_returns = (1 + returns).cumprod()
        rolling_max = cumulative_returns.expanding().max()
        drawdowns = cumulative_returns / rolling_max - 1
        max_drawdown = abs(drawdowns.min())
        
        # For single day, use total return instead of CAGR
        total_return = total_pnl / sum(abs(p.entry_price()) for p in self.positions)
        
        # MAR = Return / Max Drawdown
        mar = total_return / max_drawdown if max_drawdown != 0 else total_return
        
        # Sortino using trade returns
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std() if len(downside_returns) > 0 else 0
        sortino = total_return / downside_std if downside_std != 0 else total_return
        
        # Calculate profit factor
        gross_profit = sum(p.pnl for p in self.positions if p.pnl > 0)
        gross_loss = abs(sum(p.pnl for p in self.positions if p.pnl < 0))
        profit_factor = gross_profit / gross_loss if gross_loss != 0 else float('inf')
        
        return {
            'total_pnl': total_pnl,
            'win_rate': wins / len(self.positions),
            'num_positions': len(self.positions),
            'mar': mar,
            'sortino': sortino,
            'return': total_return * 100,  # Show as percentage
            'profit_factor': profit_factor
        }
    

    def report(self) -> None:
        metrics = self._calculate_metrics()
        duration = (self.end_time - self.start_time).total_seconds()
        logger.info(f"Duration: {duration:.2f}s")
        
        logger.info("\n=== Performance Metrics ===")
        logger.info(f"Total P&L: ${metrics['total_pnl']:.2f}")
        
        logger.info("=== Risk Metrics ===")
        logger.info(f"MAR Ratio: {metrics['mar']:.2f} (Target > 1.5) - Higher is better")
        logger.info(f"Sortino: {metrics['sortino']:.2f} (Target > 1.0) - Higher is better")
        logger.info(f"Profit Factor: {metrics['profit_factor']:.2f} (Target > 1.5) - Higher is better")
        
        logger.info("=== Trade Statistics ===")
        logger.info(f"Win Rate: {metrics['win_rate']*100:.1f}% (Target > 50%)")
        logger.info(f"Number of Positions: {metrics['num_positions']}")
        
        logger.info("=== Returns ===")
        logger.info(f"Return: {metrics['return']:.1f}% (Target > 15%)")
        
        # Add summary assessment
        logger.info("=== Summary ===")
        if metrics['mar'] > 1.5 and metrics['profit_factor'] > 1.5 and metrics['win_rate'] > 0.5:
            logger.info("✅ Strategy meets all key targets")
        else:
            logger.info("⚠️ Strategy below some targets - see above for details") 