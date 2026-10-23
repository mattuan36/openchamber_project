"""Scoring and ranking against an actual-results bracket."""

from __future__ import annotations

from dataclasses import dataclass

from .loader import Bracket
from .template import (
    ROUND_ORDER,
    ROUND_WEIGHTS,
    SLOT_IDS,
    SLOTS_BY_ID,
    TOTAL_MAX_POINTS,
    team_matches,
)

TIE_BREAK_DESCRIPTION = (
    "Rank by total points. Ties are broken by championship, Final Four, "
    "Elite Eight, Sweet 16, Round of 32, then Round of 64 correct picks, "
    "then entrant name. Tied entrants share a rank (1, 2, 2, 4)."
)


@dataclass
class EntrantScore:
    """A scored entrant; mutable only for assigning competition rank."""

    bracket: Bracket
    total: int
    round_scores: dict[str, int]
    correct_by_round: dict[str, int]
    correct: int
    pending: int
    decided: int
    accuracy: float
    rank: int = 0

    @property
    def entrant(self) -> str:
        return self.bracket.entrant

    @property
    def source_name(self) -> str:
        return self.bracket.source_name


def _empty_round_map() -> dict[str, int]:
    return {round_name: 0 for round_name in ROUND_ORDER}


def score_entrant(actual: Bracket, entrant: Bracket) -> EntrantScore:
    """Score one bracket against the actual results.

    A blank actual slot is pending: it awards no points and is excluded from
    the accuracy denominator. A blank entrant pick is worth zero but is not
    pending.
    """

    round_scores = _empty_round_map()
    correct_by_round = _empty_round_map()
    correct = 0
    total = 0
    pending = 0

    for slot_id in SLOT_IDS:
        actual_value = actual.picks.get(slot_id, "").strip()
        if not actual_value:
            pending += 1
            continue

        pick = entrant.picks.get(slot_id, "").strip()
        if not pick or not team_matches(pick, actual_value):
            continue

        round_name = SLOTS_BY_ID[slot_id].round
        weight = ROUND_WEIGHTS[round_name]
        correct += 1
        total += weight
        round_scores[round_name] += weight
        correct_by_round[round_name] += 1

    decided = len(SLOT_IDS) - pending
    accuracy = (correct / decided) if decided else 0.0

    return EntrantScore(
        bracket=entrant,
        total=total,
        round_scores=round_scores,
        correct_by_round=correct_by_round,
        correct=correct,
        pending=pending,
        decided=decided,
        accuracy=accuracy,
    )


def rank_key(score: EntrantScore) -> tuple:
    """Descending tie-break key, with a stable final name comparator."""
    return (
        -score.total,
        -score.correct_by_round["CH"],
        -score.correct_by_round["F4"],
        -score.correct_by_round["E8"],
        -score.correct_by_round["S16"],
        -score.correct_by_round["R32"],
        -score.correct_by_round["R64"],
        score.bracket.entrant.casefold(),
        score.bracket.source_name.casefold(),
    )


def _tie_key(score: EntrantScore) -> tuple:
    return (
        score.total,
        score.correct_by_round["CH"],
        score.correct_by_round["F4"],
        score.correct_by_round["E8"],
        score.correct_by_round["S16"],
        score.correct_by_round["R32"],
        score.correct_by_round["R64"],
    )


def score_all(actual: Bracket, entrants: list[Bracket]) -> list[EntrantScore]:
    """Score and rank all entrants; the actual bracket is not included."""
    scores = [score_entrant(actual, entrant) for entrant in entrants]
    scores.sort(key=rank_key)

    previous_tie: tuple | None = None
    previous_rank = 0
    for index, score in enumerate(scores, start=1):
        tie = _tie_key(score)
        if tie != previous_tie:
            previous_rank = index
            previous_tie = tie
        score.rank = previous_rank
    return scores


def maximum_points() -> int:
    return TOTAL_MAX_POINTS
