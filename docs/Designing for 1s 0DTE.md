## Designing Algorithms for 1-Second SPX 0DTE

### Key Differences from Traditional Algo Design
1. Noise vs Signal
   - Traditional indicators (RSI, MACD) become noise at 1s
   - Price action largely random walk in ultra-short term
   - Volume/order flow more predictive than price patterns

2. Time Decay Reality
   - Theta decay happens in real-time
   - Holding positions increases risk
   - Must capture edge in seconds, not minutes

3. Market Microstructure
   - Tick size matters more than trends
   - Order book dynamics drive short moves
   - Large orders create temporary imbalances

### Why Non-Directional Wins
1. Statistical Edge
   - Mean reversion stronger at 1s intervals
   - Directional predictions near impossible
   - Easier to predict "too far, too fast"

2. Risk Management
   - Can scale both sides
   - Less exposed to news/sweeps
   - More frequent but smaller edges

3. Opportunity Flow
   - Every price spike is potential setup
   - Don't need to wait for specific patterns
   - Trade frequency improves law of large numbers

### Core Design Principles
1. Speed Priority
   - Minimize calculation complexity
   - Use simple numeric thresholds
   - Avoid lookback windows >60s

2. Position Management
   - Scale fast, exit faster
   - Multiple small wins > home runs
   - Break-even moves critical

3. Risk Controls
   - Size relative to market volume
   - Auto-exit on volume spikes
   - No positions during known events

### Common Pitfalls
1. Overcomplicating Logic
   - Too many indicators
   - Complex pattern matching
   - Trying to predict direction

2. Poor Scaling
   - Fixed position sizes
   - Not adapting to volatility
   - Ignoring liquidity

3. Bad Time Management
   - Trading dead periods
   - Holding through lunch
   - Fighting high-volume trends





### Strategy Logic
- Entry: Price crosses above 20 SMA
- Exit: Profit target or stop loss hit

#### Parameters
- Short Strike Range: $5-$50 below ATM
- Spread Width: $5-$50
- Stop Loss: 50%-200% of credit received
- Profit Target: 5%-100% of credit received

#### Notes
* SPX options trade in $5 increments
* $30 OTM (below) is -15 delta

#### Result
[I 2025-03-29 16:27:28,580] Trial 410 finished with value: 0.8999999165534973 and 
parameters: {'short_strike_otm': 20, 'spread_width': 5, 'profit_pct': 0.6478348326142667, 'loss_pct': -1.9552897494806658, 'min_credit': 0.45576863610266366, 'sma_period': 171, 'rsi_period': 93, 'rsi_lower': 37.208484913334786, 'rsi_upper': 68.7977695485184, 'atr_period': 53, 'atr_threshold': 0.0005600344151306896}. Best is trial 410 with value: 0.8999999165534973.

