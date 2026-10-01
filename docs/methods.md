# Methods and implementation conventions

## Baseline model

Unless otherwise stated, the study uses a non-dividend-paying European call with:

- S0 = 100
- K = 100
- T = 1 year
- r = 0.03, continuously compounded
- sigma = 0.20

The stock follows exact risk-neutral GBM transitions in simulation.

## Pricing

`models.py` implements the Black-Scholes call value, Delta, Gamma, Vega, Theta, a Cox-Ross-Rubinstein backward-induction tree, and a plain Monte Carlo estimator using exact terminal GBM sampling.

The Monte Carlo convergence experiment uses N = 10^2, 10^3, 10^4, 10^5, and 10^6 with 50 independent replications at each N. The empirical convergence slope is fitted to log(MAE) against log(N).

The CRR study reports selected lattice sizes, evaluates every integer step count from 10 through 120 for odd-even oscillation, and estimates the even-step convergence rate on N = 20, 40, 80, 160, 320, 640, 1280.

## Discrete delta hedging

A short call is paired with a stock-and-cash replicating portfolio. The option premium funds the initial Delta position plus cash. Between hedge dates cash compounds at r. At each internal grid point the stock position is reset to analytical Black-Scholes Delta.

`steps` is the number of time intervals, so there are `steps - 1` internal rebalances. No terminal rebalance is performed.

Terminal hedge error is:

```text
stock value + cash - option payoff
```

in terminal dollars. Negative error is a replication shortfall.

The default transaction-cost convention excludes the initial stock-purchase charge and terminal liquidation charge. Internal trades incur:

```text
cost_rate * abs(change in Delta) * current stock price
```

The frictionless experiment and each transaction-cost row use 5,000 paths. Within a hedge frequency the same stock paths are reused across 0, 5, 10, and 25 bps costs.

## Gamma exposure

The implementation records the left-point proxy

G = 0.5 * sum(|Gamma| * S^2 * sigma^2 * dt).

It is a non-negative accumulated convexity-weighted variance exposure. It is not an exact decomposition of terminal hedge error and does not establish causality.

Nine scenarios combine S0 = 80, 100, 120 with T = 0.25, 0.50, 1.00. Each scenario is simulated with 5,000 paths under annual hedge frequencies 12, 52, 126, and 252.

For each frequency the study reports:

- scenario-level Pearson correlation between mean G and RMSE;
- scenario-level Spearman correlation;
- a 200,000-resample paired percentile-bootstrap interval for Pearson r;
- pooled path-level Pearson and Spearman correlations between G and absolute terminal error.

## Sensitivity analysis

The reproducible sensitivity table covers S0 in {80, 100, 120}, sigma in {0.10, 0.20, 0.50}, and T in {0.10, 0.25, 1.00, 2.00}. A separate dense analytical Gamma surface spans S from 60 to 140 and T from 0.03 to 2.0 at sigma = 0.20.
