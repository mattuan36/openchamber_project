"""Command-line entry point for the 2026 bracket scorekeeper.

Examples
--------
    python scorekeeper.py --input sample_data
    python scorekeeper.py --input sample_data --actual sample_data/2026_results.xlsx
    python scorekeeper.py --input sample_data --validate-only
    python scorekeeper.py --input sample_data --output reports/2026_report.xlsx
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from bracket.loader import (
    DEFAULT_REPORT_NAME,
    BracketError,
    Dataset,
    load_dataset,
)
from bracket.report import ReportError, write_report
from bracket.scoring import EntrantScore, TIE_BREAK_DESCRIPTION, score_all
from bracket.template import (
    ROUND_GAME_COUNTS,
    ROUND_ORDER,
    ROUND_WEIGHTS,
    SLOT_IDS,
    TOTAL_MAX_POINTS,
)


DEFAULT_OUTPUT = Path(DEFAULT_REPORT_NAME)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scorekeeper.py",
        description=(
            "Score 2026 March Madness brackets against an actual-results "
            "workbook and write a formatted five-sheet Excel report."
        ),
        epilog=(
            "The actual-results file is chosen by a filename containing "
            "'results' (case-insensitive), unless --actual is supplied. "
            "Inputs are never modified. The report contains Picks, Standings, "
            "State, Teams, and Corrections sheets and can be reopened by the "
            "Streamlit app."
        ),
    )
    parser.add_argument(
        "-i",
        "--input",
        type=Path,
        default=Path("."),
        help="A workbook, or a folder containing workbooks (default: .).",
    )
    parser.add_argument(
        "--actual",
        type=Path,
        default=None,
        metavar="PATH",
        help=(
            "Explicit actual-results workbook. Useful when the filename does "
            "not contain 'results' or when multiple candidates exist."
        ),
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Report path (default: {DEFAULT_OUTPUT}).",
    )
    parser.add_argument(
        "--skip-invalid",
        action="store_true",
        help="Skip malformed entrant files instead of stopping at the first one.",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Parse and validate inputs without writing the report.",
    )
    return parser


def _print_warnings(dataset: Dataset) -> None:
    messages: list[str] = []
    messages.extend(dataset.warnings)
    if dataset.actual.warnings:
        messages.extend(
            f"{dataset.actual.source_name}: {warning}"
            for warning in dataset.actual.warnings
        )
    for entrant in dataset.entrants:
        if entrant.warnings:
            messages.extend(
                f"{entrant.source_name}: {warning}"
                for warning in entrant.warnings
            )
    for path, message in dataset.skipped:
        messages.append(f"Skipped {path.name}: {message}")

    for message in dict.fromkeys(messages):
        print(f"Warning: {message}", file=sys.stderr)


def _print_validation(dataset: Dataset, scores: list[EntrantScore]) -> None:
    actual = dataset.actual
    print("Validation OK")
    print(f"  Actual file: {actual.source_name} ({actual.entrant})")
    print(f"  Actual picks: {actual.filled}/{len(SLOT_IDS)}")
    print(f"  Entrants: {len(dataset.entrants)}")
    if dataset.skipped:
        print(f"  Skipped entrant files: {len(dataset.skipped)}")
    print(f"  Pending games: {dataset.pending}")
    print("  Game map: " + ", ".join(
        f"{round_name}={ROUND_GAME_COUNTS[round_name]}"
        for round_name in ROUND_ORDER
    ))
    print("  Weights: " + ", ".join(
        f"{round_name}={ROUND_WEIGHTS[round_name]}"
        for round_name in ROUND_ORDER
    ))
    print(f"  Maximum points: {TOTAL_MAX_POINTS}")
    if scores:
        print("  Standings:")
        for score in scores:
            print(
                f"    {score.rank:>2}. {score.entrant}: {score.total} "
                f"({score.correct}/{score.decided}, {score.accuracy:.1%})"
            )


def _print_summary(
    dataset: Dataset, scores: list[EntrantScore], report_path: Path
) -> None:
    print(f"Report written: {report_path.resolve()}")
    print(f"Actual: {dataset.actual.source_name} ({dataset.actual.entrant})")
    print(f"Entrants: {len(dataset.entrants)}")
    print(f"Pending games: {dataset.pending}")
    if scores:
        print("Standings:")
        for score in scores[:10]:
            print(
                f"  {score.rank:>2}. {score.entrant}: {score.total} "
                f"({score.correct}/{score.decided}, {score.accuracy:.1%})"
            )
        if len(scores) > 10:
            print(f"  ... {len(scores) - 10} more in the Standings sheet")
    print(f"Tie-break: {TIE_BREAK_DESCRIPTION}")


def run(args: argparse.Namespace) -> int:
    input_path: Path = args.input
    output_path: Path = args.output
    if "results" in output_path.stem.casefold():
        raise BracketError(
            "The report filename must not contain 'results'; use "
            "bracket_report.xlsx or another name. That word identifies the "
            "actual-results input during discovery."
        )

    dataset = load_dataset(
        input_path,
        actual_path=args.actual,
        output_path=None if args.validate_only else output_path,
        skip_invalid=args.skip_invalid,
    )
    _print_warnings(dataset)

    scores = score_all(dataset.actual, dataset.entrants)
    if args.validate_only:
        _print_validation(dataset, scores)
        return 0

    report_path = write_report(dataset, scores, output_path)
    _print_summary(dataset, scores, report_path)
    return 0


def _configure_console() -> None:
    """Avoid a Windows console encoding crash on non-ASCII entrant names."""

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(errors="replace")
            except (AttributeError, ValueError):
                pass


def main(argv: Sequence[str] | None = None) -> int:
    _configure_console()
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        return run(args)
    except (BracketError, ReportError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130
    except Exception as exc:  # keep the CLI friendly, but still fail
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
