# First Complete XAUUSD Research Pipeline

Generated: 2026-08-07T08:08:28.724311+00:00  
Pipeline: `XAUUSD-M15-FIRST-001`  
Validation assessment: **not_supported**

## Scope

This is a correctness and research-validity milestone. It does not claim that the
candidate is profitable, deployable, or robust outside the fixed HistData sample.

## Reproducibility

- Source: 36 monthly HistData XAUUSD bid/ask tick Parquets, 2015-2017
- Source ticks: 76443318
- M15 rows: 70879
- Feature dataset SHA-256: `058787cdabe5bc00d7a22ad0ae7373902459a86586482a962b7e76b6510f24e2`
- Statistical report SHA-256: `7592c4f88df7afea733ba02e879516fc684ed1010377554c80aef1c34c6f7291`
- Research period: 2015; validation period: 2016; final unseen test: 2017
- Candidate SHA-256: `b0f63d6a5cbbfdcbed5f844af4adc8128352fc8e5d8fb40b9f4364522114afcc`
- Validation plan SHA-256: `285f78342889ee8af65e319a06aa0f05bd4607f01701972dff0fe6f626aedad8`

## Research Finding

Event: a fully closed bullish M15 candle with body/range >= 0.5. The predeclared
outcome was the midpoint return after 4 observed bars.

- Selected non-overlapping events: 2786
- Conditional mean: -0.0028%
- Baseline mean: -0.0017%
- Excess mean: -0.0011%
- 95% excess-mean CI: (-8.505853146149344e-05, 5.86044655043727e-05)
- Adjusted q-value: 0.6181909045477262
- Reviewed finding: `FND-XAUUSD-M15-STRONG-BULLISH-001` (rejected)

## Strategy Candidate

`XAUUSD-M15-STRONG-BULLISH-LONG-001` enters long at the next observed ask open after the event and
exits at the bid open after 4 observed bars. Its source finding was rejected,
so this frozen rule is a **pipeline probe**, not a qualifying candidate. Position sizing
is normalized 100% notional. There is no stop loss or take profit, historical spread is
paid directly, and primary slippage is zero beyond spread. The stress case adds
1.0 bps adverse slippage per side.

## Validation Results

| Split | Trades | Mean/trade | Cumulative | Max drawdown | Stress mean/trade | Criteria passed |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| research | 3159 | -0.0329% | -64.8744% | 65.3575% | -0.0529% | no |
| validation | 3193 | -0.0268% | -57.7295% | 59.0845% | -0.0467% | no |
| final_test | 3214 | -0.0267% | -57.7045% | 58.2035% | -0.0467% | no |

Predeclared evaluation criteria require at least 100 trades, positive mean
return after observed spread in both primary and stress executions, and maximum drawdown
no greater than 25.0000%. The final assessment is mechanical application of those
frozen criteria, not a profitability optimization.

## Limitations

- One instrument, one timeframe, one historical quote source, and one three-year regime.
- Tick timestamps and quotes were validated, but no provider-specific holiday/session
  calendar is available.
- Market impact, latency, rejected fills, swaps, financing, and broker contract sizing
  are not modeled.
- Holding periods count observed bars, so a position may span a session gap.
- The bootstrap treats the unconditional baseline mean as fixed and only partially
  addresses serial dependence.
- The final-test result must not be used to revise revision 1; any change requires a new
  candidate revision and a new unseen period.
