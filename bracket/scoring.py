"""Scoring and ranking against an actual-results bracket."""

from __future__ import annotations

from dataclasses import dataclass

from .loader import Bracket
from .template import (
    DOWNSTREAM_BY_ID,
    ROUND_ORDER,
    ROUND_WEIGHTS,
    SLOT_IDS,
    SLOTS_BY_ID,
    TOTAL_MAX_POINTS,
    normalize_team,
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


@dataclass(frozen=True)
class GameResult:
    """The outcome of one slot for one entrant."""

    slot_id: str
    round: str
    region: str | None
    weight: int
    actual: str
    pick: str
    status: str  # "correct", "incorrect", or "pending"
    points: int

    @property
    def correct(self) -> bool:
        return self.status == "correct"

    @property
    def pending(self) -> bool:
        return self.status == "pending"


def score_games(actual: Bracket, entrant: Bracket) -> list[GameResult]:
    """Return per-game status and points in canonical slot order.

    A blank actual result is pending: it awards no points and is never counted
    as incorrect. A blank entrant pick is incorrect once the game is decided.
    """

    results: list[GameResult] = []
    for slot_id in SLOT_IDS:
        actual_value = actual.picks.get(slot_id, "").strip()
        pick = entrant.picks.get(slot_id, "").strip()
        slot = SLOTS_BY_ID[slot_id]
        weight = ROUND_WEIGHTS[slot.round]
        if not actual_value:
            status = "pending"
        elif pick and team_matches(pick, actual_value):
            status = "correct"
        else:
            status = "incorrect"
        results.append(
            GameResult(
                slot_id=slot_id,
                round=slot.round,
                region=slot.region,
                weight=weight,
                actual=actual_value,
                pick=pick,
                status=status,
                points=weight if status == "correct" else 0,
            )
        )
    return results


def available_picks(
    slot_id: str,
    team_pairs: dict[str, tuple[str, ...]],
    picks: dict[str, str],
) -> list[str]:
    """Teams legally available for a slot given the current feeder picks.

    First-round games offer both printed teams. Later rounds offer the current
    feeder winners; if either feeder is still pending, no team is known yet and
    the caller should present only the pending option.
    """

    slot = SLOTS_BY_ID.get(slot_id)
    if slot is None:
        return []
    if slot.round == "R64" or not slot.feeders:
        return list(dict.fromkeys(team_pairs.get(slot_id, ())))
    options: list[str] = []
    for feeder in slot.feeders:
        value = picks.get(feeder, "").strip()
        if value and not any(team_matches(value, option) for option in options):
            options.append(value)
    return options


def _winners(
    slot_id: str,
    picks: dict[str, str],
    team_pairs: dict[str, tuple[str, ...]],
) -> set[str]:
    """Normalized teams that can still win a slot given decided results."""

    pick = picks.get(slot_id, "").strip()
    if pick:
        return {normalize_team(pick)}
    return _contenders(slot_id, picks, team_pairs)


def _contenders(
    slot_id: str,
    picks: dict[str, str],
    team_pairs: dict[str, tuple[str, ...]],
) -> set[str]:
    """Normalized teams that can still reach (and therefore win) a slot."""

    slot = SLOTS_BY_ID[slot_id]
    if slot.round == "R64" or not slot.feeders:
        return {
            normalize_team(team)
            for team in team_pairs.get(slot_id, ())
            if normalize_team(team)
        }
    possible: set[str] = set()
    for feeder in slot.feeders:
        possible |= _winners(feeder, picks, team_pairs)
    return possible


def _descendants(slot_id: str) -> list[str]:
    found: set[str] = set()
    queue = [slot_id]
    while queue:
        parent = queue.pop(0)
        for child in DOWNSTREAM_BY_ID.get(parent, ()):
            if child not in found:
                found.add(child)
                queue.append(child)
    return [candidate for candidate in SLOT_IDS if candidate in found]


def cascade_clear(
    picks: dict[str, str],
    changed_slot: str,
    team_pairs: dict[str, tuple[str, ...]] | None = None,
) -> tuple[dict[str, str], list[str]]:
    """Clear downstream picks that can no longer be produced by their feeders.

    With team pairs, the check follows the whole downstream subtree: a pick is
    impossible when it is not among the teams that can still reach that slot.
    This propagates through several rounds when a feeder winner changes. Without
    team pairs, a conservative feeder-only check is used.
    """

    cleared_picks = dict(picks)
    cleared: list[str] = []

    if team_pairs:
        for slot_id in _descendants(changed_slot):
            pick = cleared_picks.get(slot_id, "").strip()
            if not pick:
                continue
            possible = _contenders(slot_id, cleared_picks, team_pairs)
            if normalize_team(pick) not in possible:
                cleared_picks[slot_id] = ""
                cleared.append(slot_id)
        return cleared_picks, cleared

    queue = [changed_slot]
    while queue:
        parent = queue.pop(0)
        for child in DOWNSTREAM_BY_ID.get(parent, ()):
            feeders = SLOTS_BY_ID[child].feeders
            feeder_picks = [cleared_picks.get(feeder, "").strip() for feeder in feeders]
            if not all(feeder_picks):
                continue
            pick = cleared_picks.get(child, "").strip()
            if pick and not any(team_matches(pick, value) for value in feeder_picks):
                cleared_picks[child] = ""
                cleared.append(child)
                queue.append(child)
    return cleared_picks, cleared


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

    for result in score_games(actual, entrant):
        if result.pending:
            pending += 1
            continue
        if not result.correct:
            continue
        correct += 1
        total += result.points
        round_scores[result.round] += result.points
        correct_by_round[result.round] += 1

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
