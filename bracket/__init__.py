"""Reusable core for the March Madness bracket scorekeeper."""

from .loader import (
    Bracket,
    BracketError,
    Dataset,
    discover_files,
    is_generated_report,
    load_dataset,
    parse_bracket,
    select_actual_file,
)
from .report import ReportError, build_report, default_state, write_report
from .scoring import (
    EntrantScore,
    GameResult,
    available_picks,
    cascade_clear,
    score_all,
    score_entrant,
    score_games,
)
from .store import (
    FolderScan,
    ReportLoadError,
    ReportSession,
    build_from_raw,
    load_report,
    rebuild_from_raw,
    scan_folder,
)
from .template import (
    ROUND_ORDER,
    ROUND_WEIGHTS,
    SLOT_IDS,
    TOTAL_MAX_POINTS,
    normalize_team,
    team_matches,
)

__all__ = [
    "Bracket",
    "BracketError",
    "Dataset",
    "EntrantScore",
    "FolderScan",
    "GameResult",
    "ROUND_ORDER",
    "ROUND_WEIGHTS",
    "ReportError",
    "ReportLoadError",
    "ReportSession",
    "SLOT_IDS",
    "TOTAL_MAX_POINTS",
    "available_picks",
    "build_from_raw",
    "build_report",
    "cascade_clear",
    "default_state",
    "discover_files",
    "is_generated_report",
    "load_dataset",
    "load_report",
    "normalize_team",
    "parse_bracket",
    "rebuild_from_raw",
    "scan_folder",
    "score_all",
    "score_entrant",
    "score_games",
    "select_actual_file",
    "team_matches",
    "write_report",
]
