"""Command-line interface for the reproducible option-pricing study."""

import argparse
import json
from pathlib import Path

from .experiments import DEFAULT_CONFIG, run_study, verify_reproduction


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    reproduce = commands.add_parser("reproduce", help="Rebuild all study data, statistics, figures, and LaTeX assets")
    reproduce.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    reproduce.add_argument("--output", type=Path, default=Path("reproducible"))
    reproduce.add_argument("--quick", action="store_true", help="Smaller smoke-run grid for development/CI; not the paper dataset")
    reproduce.add_argument("--force", action="store_true", help="Replace an existing output directory")

    verify = commands.add_parser("verify", help="Regenerate the full study and verify scientific equivalence with the committed outputs")
    verify.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    verify.add_argument("--reference", type=Path, default=Path("reproducible"))
    verify.add_argument("--output", type=Path, default=Path("results/verification"))
    verify.add_argument("--force", action="store_true", help="Replace an existing verification output directory")

    args = parser.parse_args(argv)
    try:
        if args.command == "reproduce":
            report = run_study(args.output, config_path=args.config, quick=args.quick, replace=args.force)
            stats = report["statistics"]
            print(json.dumps({
                "output": str(args.output),
                "mode": report["metadata"]["mode"],
                "black_scholes": stats["black_scholes"],
                "mc_slope": stats["monte_carlo"]["slope"],
                "crr_even_slope": stats["crr_even"]["slope"],
                "weekly_gamma_pearson": stats["gamma_correlations"]["Weekly"]["pearson"],
            }, indent=2))
        else:
            report = verify_reproduction(args.reference, args.output, config_path=args.config, replace=args.force)
            print(json.dumps(report, indent=2))
            if not report["matched"]:
                parser.exit(1, "Reproduction check failed: regenerated outputs differ beyond the scientific tolerance.\n")
    except (ValueError, FileNotFoundError) as exc:
        parser.exit(2, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
