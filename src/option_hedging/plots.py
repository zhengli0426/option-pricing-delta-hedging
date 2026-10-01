"""Generate all numerical figures from reproducible study outputs."""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
import pandas as pd

from .models import call_gamma

NAVY = "#264653"
TEAL = "#2A9D8F"
BLUE = "#5B8EAD"
GREY = "#6B7280"
GRID = "#D8E0E5"
STYLE = {
    "font.family": "DejaVu Serif",
    "font.size": 10.5,
    "axes.labelsize": 11,
    "legend.fontsize": 9,
    "xtick.labelsize": 9.5,
    "ytick.labelsize": 9.5,
    "axes.linewidth": 0.8,
    "grid.linewidth": 0.6,
    "savefig.dpi": 220,
}
GAMMA_CMAP = LinearSegmentedColormap.from_list(
    "gamma_blue_green", ["#F3F6F5", "#DCEAE6", "#A9CEC5", "#5FA89D", "#2D6F78"]
)


def _table(data_dir: Path, filename: str, columns: tuple[str, ...]) -> pd.DataFrame:
    frame = pd.read_csv(data_dir / filename)
    missing = set(columns) - set(frame.columns)
    if missing:
        raise ValueError(f"{filename} is missing columns: {', '.join(sorted(missing))}")
    if frame.empty:
        raise ValueError(f"{filename} contains no observations")
    for column in columns:
        frame[column] = pd.to_numeric(frame[column], errors="raise")
        if not np.isfinite(frame[column].to_numpy(dtype=float)).all():
            raise ValueError(f"{filename}: {column} must contain finite values")
    return frame


def _grid(ax: plt.Axes, *, logarithmic: bool = False) -> None:
    ax.grid(True, which="both" if logarithmic else "major", linestyle="--", color=GRID, alpha=0.7)
    ax.set_axisbelow(True)


def _save(fig: plt.Figure, output_dir: Path, name: str) -> Path:
    target = output_dir / name
    fig.savefig(target, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return target


def make_figures(data_dir: Path, output_dir: Path, *, config: dict) -> list[Path]:
    """Generate the seven paper figures from deterministic numerical outputs."""
    data_dir, output_dir = Path(data_dir), Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    mc = _table(data_dir, "monte_carlo_convergence.csv", ("N", "MAE"))
    dense = _table(data_dir, "crr_dense.csv", ("N", "Signed_error"))
    hedging = _table(data_dir, "frictionless_hedging.csv", ("Steps", "RMSE"))
    exposure = _table(data_dir, "gamma_exposure_scenarios.csv", ("Steps_per_year", "T", "Gamma_exposure", "RMSE"))
    costs = _table(data_dir, "transaction_cost_sensitivity.csv", ("Steps", "Cost_bps", "RMSE"))
    exposure = exposure.loc[exposure["Steps_per_year"] == 52].copy()
    if exposure.empty:
        raise ValueError("Weekly Gamma-exposure scenarios are required")

    mc = mc.sort_values("N")
    dense = dense.sort_values("N")
    hedging = hedging.sort_values("Steps")
    cost_matrix = costs.pivot(index="Cost_bps", columns="Steps", values="RMSE").sort_index().sort_index(axis=1)
    if cost_matrix.isna().any().any():
        raise ValueError("Transaction-cost table must contain a complete grid")

    p = config["parameters"]
    written: list[Path] = []
    with plt.rc_context(STYLE):
        n = mc["N"].to_numpy()
        mae = mc["MAE"].to_numpy()
        slope, intercept = np.polyfit(np.log(n), np.log(mae), 1)
        fig, ax = plt.subplots(figsize=(7.2, 4.8), layout="constrained")
        ax.loglog(n, mae, "o-", color=NAVY, lw=1.8, ms=5.5, label="Monte Carlo MAE")
        ax.loglog(n, np.exp(intercept) * n**slope, "--", color=TEAL, lw=1.5, label=fr"Empirical slope $\approx {slope:.3f}$")
        ax.loglog(n, mae[0] * (n / n[0])**-0.5, ":", color=GREY, lw=1.5, label=r"Reference slope $=-0.5$")
        ax.set(xlabel=r"Number of simulations $N$", ylabel="Mean absolute error (MAE)")
        _grid(ax, logarithmic=True)
        ax.legend(framealpha=0.95)
        written.append(_save(fig, output_dir, "mc_convergence.png"))

        fig, ax = plt.subplots(figsize=(7.2, 4.8), layout="constrained")
        steps = dense["N"].to_numpy(dtype=int)
        errors = dense["Signed_error"].to_numpy()
        for parity, label, color, marker in ((1, "Odd steps", TEAL, "o"), (0, "Even steps", BLUE, "s")):
            mask = steps % 2 == parity
            ax.vlines(steps[mask], 0, errors[mask], color=color, lw=0.7, alpha=0.5)
            ax.plot(steps[mask], errors[mask], marker, color=color, ms=3.5, label=label)
        ax.axhline(0, color=GREY, lw=1, ls="--")
        ax.set(xlabel=r"Number of binomial steps $N$", ylabel=r"Pricing error (CRR $-$ Black--Scholes)")
        _grid(ax)
        ax.legend(framealpha=0.95)
        written.append(_save(fig, output_dir, "crr_oscillation.png"))

        prices, times = np.meshgrid(np.linspace(60, 140, 110), np.linspace(0.03, 2, 110))
        gamma = call_gamma(prices, float(p["strike"]), times, float(p["rate"]), float(p["volatility"]))
        fig = plt.figure(figsize=(8, 5.7), layout="constrained")
        ax = fig.add_subplot(111, projection="3d")
        surface = ax.plot_surface(prices, times, gamma, cmap=GAMMA_CMAP, rcount=110, ccount=110, vmin=0, vmax=float(np.max(gamma)), linewidth=0, antialiased=True)
        ax.set_xlabel(r"Underlying price $S$", labelpad=9)
        ax.set_ylabel(r"Time to maturity $T$ (years)", labelpad=10)
        ax.set_zlabel(r"Gamma $\Gamma$", labelpad=9)
        ax.view_init(elev=27, azim=-60)
        colorbar = fig.colorbar(surface, ax=ax, shrink=0.65, pad=0.09)
        colorbar.set_label(r"Gamma $\Gamma$")
        written.append(_save(fig, output_dir, "gamma_surface.png"))

        fig, ax = plt.subplots(figsize=(7.2, 4.8), layout="constrained")
        positions = np.arange(len(hedging))
        heights = hedging["RMSE"].to_numpy()
        colors = GAMMA_CMAP(np.linspace(0.45, 0.95, len(hedging)))
        bars = ax.bar(positions, heights, color=colors, width=0.58, edgecolor="white", linewidth=0.8)
        ax.plot(positions, heights, "o--", color=NAVY, lw=1.4, ms=5)
        ax.set_xticks(positions, [f"{value:g}" for value in hedging["Steps"]])
        ax.set(xlabel="Rebalancing frequency (steps per year)", ylabel="Hedging RMSE")
        ax.set_ylim(0, max(heights) * 1.15)
        ax.bar_label(bars, labels=[f"{value:.4f}" for value in heights], padding=5, fontsize=9, color=NAVY)
        ax.grid(axis="y", linestyle="--", color=GRID, alpha=0.7)
        ax.set_axisbelow(True)
        written.append(_save(fig, output_dir, "hedging_rmse.png"))

        fig, ax = plt.subplots(figsize=(7.2, 4.8), layout="constrained")
        for label, color, marker in (("OTM", BLUE, "o"), ("ATM", NAVY, "s"), ("ITM", TEAL, "^")):
            group = exposure.loc[exposure["Moneyness"] == label].sort_values("T")
            ax.scatter(group["Gamma_exposure"], group["RMSE"], s=65, marker=marker, color=color, label=label, edgecolor="white", linewidth=0.7, zorder=3)
            offset = (5, -14) if label == "OTM" else (5, 6)
            for row in group.itertuples():
                ax.annotate(f"T={row.T:.2f}", (row.Gamma_exposure, row.RMSE), xytext=offset, textcoords="offset points", fontsize=8)
        coefficients = np.polyfit(exposure["Gamma_exposure"], exposure["RMSE"], 1)
        domain = np.linspace(exposure["Gamma_exposure"].min(), exposure["Gamma_exposure"].max(), 100)
        ax.plot(domain, np.polyval(coefficients, domain), "--", color=GREY, lw=1.3, label="Descriptive linear fit")
        ax.set(xlabel="Mean integrated Gamma exposure", ylabel="Weekly hedging RMSE")
        ax.margins(x=0.14, y=0.15)
        _grid(ax)
        ax.legend(framealpha=0.95, loc="lower right")
        written.append(_save(fig, output_dir, "gamma_exposure_rmse.png"))

        fig, ax = plt.subplots(figsize=(7.2, 4.8), layout="constrained")
        values = cost_matrix.to_numpy()
        heatmap = ax.imshow(values, cmap=GAMMA_CMAP, aspect="auto")
        ax.set_xticks(np.arange(len(cost_matrix.columns)), [f"{value:g}" for value in cost_matrix.columns])
        ax.set_yticks(np.arange(len(cost_matrix.index)), [f"{value:g}" for value in cost_matrix.index])
        ax.set(xlabel="Rebalancing frequency (steps per year)", ylabel="Proportional transaction cost (basis points)")
        for (row, column), value in np.ndenumerate(values):
            red, green, blue, _ = heatmap.cmap(heatmap.norm(value))
            brightness = 0.2126 * red + 0.7152 * green + 0.0722 * blue
            ax.text(column, row, f"{value:.4f}", ha="center", va="center", fontsize=10, color="white" if brightness < 0.57 else NAVY)
        fig.colorbar(heatmap, ax=ax, label="Hedging RMSE", shrink=0.9, pad=0.03)
        written.append(_save(fig, output_dir, "transaction_cost_heatmap.png"))

    return written
