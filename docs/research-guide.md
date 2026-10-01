# Five-minute research guide

This repository asks four linked questions about a European call option.

First, how do plain Monte Carlo and the CRR tree converge to the Black-Scholes benchmark? The Monte Carlo experiment tests the expected square-root error law, while the CRR experiment shows deterministic odd-even lattice oscillation and an approximately first-order even-step error pattern.

Second, where are option sensitivities concentrated? Analytical Greeks show that Gamma becomes sharply concentrated near the strike as maturity shortens, which motivates studying discrete hedge error in that region.

Third, how does hedge frequency affect replication risk? The study simulates monthly, weekly, approximately twice-weekly, and daily delta hedging. In the frictionless model, RMSE falls markedly as the hedge grid becomes finer. Across moneyness and maturity scenarios, integrated Gamma exposure is strongly associated with scenario-level hedging RMSE, while the weaker path-level association provides an important limitation on that interpretation.

Fourth, what changes when trading costs are introduced? Reusing the same simulated paths across cost rates shows that more frequent hedging is not automatically better once proportional costs become large enough.

For exact values, start with `reproducible/statistics.json` and the generated CSV files. For implementation details, read `docs/methods.md`. For the complete research narrative, read `paper/paper.pdf`.
