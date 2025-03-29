import optuna
from examples.putspread.strategy import PutSpread
from backtester import Backtest
from backtester.loaders import OptionQuoteLoader, IndexQuoteLoader, IndexOHLCLoader
from loguru import logger
import os
from datetime import datetime

def objective(trial):
    strategy = PutSpread(
        short_strike=trial.suggest_int('short_strike_otm', 5, 50, step=5),
        spread_width=trial.suggest_int('spread_width', 5, 50, step=5),
        profit_pct=trial.suggest_float('profit_pct', 0.05, 1.0),
        loss_pct=trial.suggest_float('loss_pct', -2.0, -0.5),
        min_credit=trial.suggest_float('min_credit', 0.05, 0.50),

        # Technical indicators
        sma_period=trial.suggest_int('sma_period', 60, 300),  # 1-5 minutes
        rsi_period=trial.suggest_int('rsi_period', 30, 120),  # 30s-2min
        rsi_lower=trial.suggest_float('rsi_lower', 25, 40),
        rsi_upper=trial.suggest_float('rsi_upper', 60, 75),
        atr_period=trial.suggest_int('atr_period', 30, 120),  # 30s-2min
        atr_threshold=trial.suggest_float('atr_threshold', 0.0001, 0.001)  # 0.01-0.1% for 1s data
    )
    
    chains = OptionQuoteLoader('20250102', interval=1000).load()
    index_quotes = IndexQuoteLoader('20250102').load()
    index_ohlc = IndexOHLCLoader('20250102').load()
    
    index_quotes = strategy.prepare_indicators(index_quotes, index_ohlc)
    backtest = Backtest(chains, index_quotes, strategy)
    metrics = backtest.run()
    
    # Log trial results
    logger.info(f"Trial {trial.number}:")
    logger.info(f"  MAR: {metrics['mar']:.2f}")
    logger.info(f"  Win Rate: {metrics['win_rate']:.1%}")
    logger.info(f"  Return: {metrics['return']:.1f}%")
    logger.info(f"  Num Trades: {metrics['num_positions']}")
    
    return metrics['mar']

if __name__ == "__main__":
    if os.path.exists("optuna.db"):
        os.remove("optuna.db")

    results_dir = "examples/putspread/optuna_results"
    os.makedirs(results_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    db_path = f"{results_dir}/optuna_{timestamp}.db"

    study = optuna.create_study(
        direction='maximize',
        storage=f"sqlite:///{db_path}?timeout=60",
        study_name=f"putspread_opt_{timestamp}"
    )
    
    # Run more trials since we have more parameters
    study.optimize(objective, n_trials=1000, n_jobs=8)

    # Print best results
    trial = study.best_trial
    logger.info("\nBest trial:")
    logger.info(f"  Value: {trial.value:.2f}")
    logger.info("\nParameters:")
    for key, value in trial.params.items():
        logger.info(f"  {key}: {value}")
    
    # Save results to CSV
    results_df = study.trials_dataframe()
    results_df.to_csv(f"{results_dir}/results_{timestamp}.csv")
    logger.info(f"\nResults saved to {results_dir}/results_{timestamp}.csv") 