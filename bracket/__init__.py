"""Reusable core for the March Madness bracket scorekeeper."""

from .loader import (
    Bracket,
    BracketError,
    Dataset,
    discover_files,
    load_dataset,
    parse_bracket,
    select_actual_file,
)
from .scoring import EntrantScore, score_all, score_entrant
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
    "ROUND_ORDER",
    "ROUND_WEIGHTS",
    "SLOT_IDS",
    "TOTAL_MAX_POINTS",
    "discover_files",
    "load_dataset",
    "normalize_team",
    "parse_bracket",
    "score_all",
    "score_entrant",
    "select_actual_file",
    "team_matches",
]
