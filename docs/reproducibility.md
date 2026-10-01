# Reproducibility protocol

The final repository uses one executable pipeline for every numerical result reported in the manuscript.

## Scientific source of truth

`config/study.json` defines the model parameters, experiment grids, path counts, Monte Carlo replications, transaction-cost rates, and master/bootstrap seeds. `python -m option_hedging reproduce --force` reads that configuration and rebuilds the complete `reproducible/` directory.

The pipeline creates:

- `data/monte_carlo_convergence.csv`
- `data/crr_convergence.csv`, `crr_dense.csv`, and `crr_even_convergence.csv`
- `data/frictionless_hedging.csv`
- `data/transaction_cost_sensitivity.csv`
- `data/gamma_exposure_scenarios.csv`
- `data/gamma_pathwise_correlations.csv`
- `data/sensitivity_grid.csv`
- `data/seed_manifest.csv`
- `statistics.json`
- all numerical paper figures
- `paper_values.tex` and generated LaTeX tables
- `metadata.json`
- `manifest.json`

The paper imports the generated `.tex` files directly, which prevents manually edited manuscript numbers from drifting away from the code outputs.

## Random-number policy

The study has a master seed of `20260925`. Each stochastic experiment receives a deterministic semantic seed derived from the master seed and a human-readable experiment label using SHA-256. For example, the seed associated with `hedging/frequency=52` is stable even if another experiment is added elsewhere in the pipeline.

Every derived seed is exported in `data/seed_manifest.csv`.

The scenario-level Gamma bootstrap uses the separately documented seed `20260923` and 200,000 attempted resamples for each hedge frequency.

## Common-random-number convention

Within a given hedge frequency, all four transaction-cost rates use the same seed and therefore the same underlying simulated stock paths. Consequently, the 0 bps slice of `transaction_cost_sensitivity.csv` is exactly the frictionless experiment rather than a separate stochastic run.

Different hedge frequencies and Gamma scenarios use distinct semantic seeds.

## Dependency lock

`requirements-lock.txt` records the exact package versions used for the committed run. The GitHub Actions reference workflow additionally pins Python 3.13.5, matching the committed run metadata. The project metadata retains compatible version ranges for ordinary installation, while the pinned reference environment is the preferred route for verification.

## Verification

After installing the locked environment, run:

```bash
python -m option_hedging verify --force
```

This regenerates the full study into `results/verification/` and checks the regenerated scientific outputs against the committed output set defined by `reproducible/manifest.json`. Primary numeric CSV and JSON outputs are compared with tight tolerances (`rel=1e-10`, `abs=5e-12`), while generated LaTeX fragments are compared byte-for-byte. For CRR tables, the primary lattice price is compared across runs and the signed, absolute, and percentage-error columns are validated against each run's own Black--Scholes benchmark. This avoids false failures caused by subtraction amplifying harmless last-bit differences. The manifest still stores exact SHA-256 fingerprints as provenance for the committed files, but CI does not require byte-identical floating-point serialization across different CPUs or numerical-library builds.

PNG rendering is excluded because anti-aliasing and font rasterisation can vary across operating systems even when the underlying numerical values are scientifically equivalent.

## Deliberate exclusion of wall-clock runtime

Runtime is not treated as a scientific result in the final manuscript. A measured duration depends on CPU, BLAS build, Python version, process scheduling, warm-up, and other machine-specific details. Removing runtime from the reported conclusions makes the numerical study more reproducible and avoids presenting a hardware benchmark as a model property.
