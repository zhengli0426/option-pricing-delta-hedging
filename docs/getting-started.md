# Getting Started

This repository is organized as a single-source, fully reproducible research project. The key numerical results, tables, and quantitative figures reported in the paper are generated directly from the current Python implementation and do not depend on a separate archived dataset.

## Recommended workflow

Run the following commands from the repository root.

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pip install -e . --no-deps
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m option_hedging reproduce --force
```

### macOS / Linux

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m pip install -e . --no-deps
.venv/bin/python -m pytest
.venv/bin/python -m option_hedging reproduce --force
```

After the full reproduction run, the `reproducible/` directory is rebuilt with:

- experiment-level CSV outputs;
- `statistics.json`;
- figures used by the paper;
- generated LaTeX values and tables imported by the manuscript;
- the deterministic random seed assigned to each experiment;
- a SHA-256 provenance manifest for the committed scientific outputs.

To verify that the current repository regenerates scientifically equivalent outputs within the project's tight floating-point tolerance, run:

```powershell
.\.venv\Scripts\python.exe -m option_hedging verify --force
```

or, on macOS / Linux:

```bash
.venv/bin/python -m option_hedging verify --force
```

## Compile the paper

First run the full reproduction command, then enter the `paper/` directory:

```bash
cd paper
latexmk -pdf main.tex
```

The manuscript imports numerical values, tables, and figures from `../reproducible/`. When compiling on Overleaf, preserve both the `paper/` and `reproducible/` directories and keep their relative paths unchanged.

## Quick mode is only for development

The command below performs a smaller smoke run with fewer simulated paths and fewer Monte Carlo repetitions:

```bash
python -m option_hedging reproduce --quick --output results/quick
```

The `--quick` output is intended for development and continuous-integration checks. It is not the dataset used in the paper.
