"""Scoring, pending-state, accuracy, and ranking tests."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from bracket.loader import Bracket, parse_bracket
from bracket.scoring import (
    GameResult,
    available_picks,
    cascade_clear,
    maximum_points,
    score_all,
    score_entrant,
    score_games,
)
from bracket.template import TOTAL_MAX_POINTS


def _bracket(actual: Bracket, name: str, changes: dict[str, str] | None = None) -> Bracket:
    picks = dict(actual.picks)
    if changes:
        picks.update(changes)
    return replace(
        actual,
        entrant=name,
        source_name=f"{name}.xlsx",
        picks=picks,
    )


def _blank_picks(actual: Bracket, name: str) -> Bracket:
    return replace(
        actual,
        entrant=name,
        source_name=f"{name}.xlsx",
        picks={slot_id: "" for slot_id in actual.picks},
    )


def test_perfect_bracket_scores_148(sample_csv: Path) -> None:
    actual = parse_bracket(sample_csv)
    entrant = _bracket(actual, "PERFECT")
    score = score_entrant(actual, entrant)
    assert maximum_points() == TOTAL_MAX_POINTS == 148
    assert score.total == 148
    assert score.correct == 63
    assert score.correct_by_round == {
        "R64": 32,
        "R32": 16,
        "S16": 8,
        "E8": 4,
        "F4": 2,
        "CH": 1,
    }
    assert score.round_scores == {
        "R64": 32,
        "R32": 32,
        "S16": 32,
        "E8": 24,
        "F4": 16,
        "CH": 12,
    }
    assert score.pending == 0
    assert score.decided == 63
    assert score.accuracy == 1.0


def test_wrong_championship_costs_12(sample_csv: Path) -> None:
    actual = parse_bracket(sample_csv)
    entrant = _bracket(actual, "CHRIS", {"CH": "Houston"})
    score = score_entrant(actual, entrant)
    assert score.total == 136
    assert score.correct == 62
    assert score.round_scores["CH"] == 0
    assert score.accuracy == 62 / 63


def test_wrong_round_pick_costs_its_weight(sample_csv: Path) -> None:
    actual = parse_bracket(sample_csv)
    for slot_id, expected in (("R64-E1", 147), ("R32-E1", 146), ("S16-E1", 144)):
        entrant = _bracket(actual, "WRONG", {slot_id: "Not A Team"})
        score = score_entrant(actual, entrant)
        assert score.total == expected
        assert score.correct == 62


def test_blank_actual_results_are_pending_not_incorrect(sample_csv: Path) -> None:
    actual = parse_bracket(sample_csv)
    actual = replace(
        actual,
        picks={
            **actual.picks,
            "CH": "",
            "F4-1": "",
        },
    )
    entrant = _bracket(actual, "MATT")
    score = score_entrant(actual, entrant)
    assert score.pending == 2
    assert score.decided == 61
    assert score.correct == 61
    assert score.total == 128
    assert score.round_scores["F4"] == 8
    assert score.round_scores["CH"] == 0
    assert score.accuracy == 1.0

    # A pick on a pending game cannot be counted wrong or right.
    entrant = _bracket(actual, "WRONG-PENDING", {"CH": "Houston"})
    score = score_entrant(actual, entrant)
    assert score.total == 128
    assert score.correct == 61
    assert score.pending == 2
    assert score.accuracy == 1.0


def test_blank_entrant_pick_is_incorrect_once_actual_is_decided(
    sample_csv: Path,
) -> None:
    actual = parse_bracket(sample_csv)
    entrant = _bracket(actual, "BLANK", {"CH": ""})
    score = score_entrant(actual, entrant)
    assert score.pending == 0
    assert score.decided == 63
    assert score.correct == 62
    assert score.total == 136
    assert score.accuracy == 62 / 63


def test_accuracy_excludes_pending_games(sample_csv: Path) -> None:
    actual = parse_bracket(sample_csv)
    actual = replace(actual, picks={**actual.picks, "R64-E1": ""})
    wrong = _bracket(actual, "WRONG", {"CH": "Houston"})
    score = score_entrant(actual, wrong)
    assert score.pending == 1
    assert score.decided == 62
    assert score.correct == 61
    assert score.accuracy == 61 / 62


def test_tie_break_prefers_championship_then_earlier_rounds(
    sample_csv: Path,
) -> None:
    actual = parse_bracket(sample_csv)

    # A: championship right, two Elite Eight games wrong -> 136.
    # B: championship wrong, Elite Eight right -> 136.
    a = _bracket(actual, "A", {"E8-E1": "Wrong", "E8-S1": "Wrong"})
    b = _bracket(actual, "B", {"CH": "Houston"})
    scores = score_all(actual, [b, a])
    assert [score.entrant for score in scores] == ["A", "B"]
    assert [score.total for score in scores] == [136, 136]
    assert scores[0].correct_by_round["CH"] == 1
    assert scores[1].correct_by_round["CH"] == 0


def test_competition_ranking_is_1_2_2_4(sample_csv: Path) -> None:
    actual = parse_bracket(sample_csv)
    first = _bracket(actual, "FIRST")
    second_a = _bracket(actual, "SECOND-A", {"CH": "Houston"})
    second_b = _bracket(actual, "SECOND-B", {"CH": "Houston"})
    fourth = _blank_picks(actual, "FOURTH")
    scores = score_all(actual, [fourth, second_b, first, second_a])
    assert [score.entrant for score in scores] == [
        "FIRST",
        "SECOND-A",
        "SECOND-B",
        "FOURTH",
    ]
    assert [score.rank for score in scores] == [1, 2, 2, 4]


def test_name_breaks_a_statistical_tie(sample_csv: Path) -> None:
    actual = parse_bracket(sample_csv)
    alpha = _bracket(actual, "ALPHA", {"CH": "Houston"})
    beta = _bracket(actual, "BETA", {"CH": "Houston"})
    scores = score_all(actual, [beta, alpha])
    assert [score.entrant for score in scores] == ["ALPHA", "BETA"]
    assert [score.rank for score in scores] == [1, 1]


def test_score_all_does_not_include_the_actual_bracket(sample_csv: Path) -> None:
    actual = parse_bracket(sample_csv)
    scores = score_all(actual, [])
    assert scores == []


def test_score_games_reports_correct_incorrect_and_pending(sample_csv: Path) -> None:
    actual = parse_bracket(sample_csv)
    actual = replace(actual, picks={**actual.picks, "CH": ""})
    entrant = _bracket(
        actual,
        "MIXED",
        {"R64-E1": "Wrong", "CH": "Houston"},
    )
    results = score_games(actual, entrant)
    by_slot = {result.slot_id: result for result in results}
    assert len(results) == 63
    assert all(isinstance(result, GameResult) for result in results)
    assert by_slot["R64-E1"].status == "incorrect"
    assert by_slot["R64-E1"].points == 0
    assert by_slot["R64-E2"].status == "correct"
    assert by_slot["R64-E2"].points == 1
    assert by_slot["CH"].status == "pending"
    assert by_slot["CH"].points == 0
    assert by_slot["CH"].pick == "Houston"


def test_available_picks_and_cascade_clearing(sample_csv: Path) -> None:
    actual = parse_bracket(sample_csv)
    pairs = actual.team_pairs
    assert available_picks("R64-E1", pairs, actual.picks) == ["Duke", "Siena"]
    assert available_picks("R32-E1", pairs, actual.picks) == ["Duke", "Ohio State"]

    picks = dict(actual.picks)
    picks["R64-E1"] = "Siena"
    cleared_picks, cleared = cascade_clear(picks, "R64-E1")
    assert cleared == ["R32-E1"]
    assert cleared_picks["R32-E1"] == ""

    # With team pairs, impossible picks clear transitively through the subtree.
    picks = dict(actual.picks)
    picks["R64-E1"] = "Siena"
    transitive, cleared = cascade_clear(picks, "R64-E1", pairs)
    assert cleared == ["R32-E1", "S16-E1", "E8-E1"]
    assert transitive["R32-E1"] == ""
    assert transitive["S16-E1"] == ""
    assert transitive["E8-E1"] == ""
    assert transitive["F4-1"] == "Houston"
    assert transitive["CH"] == "Arizona"

    # Incomplete feeders leave a downstream pick alone: it may still be possible.
    picks = dict(actual.picks)
    for slot_id in ("R64-E1", "R64-E2"):
        picks[slot_id] = ""
    picks["R32-E1"] = "Duke"
    unchanged, cleared = cascade_clear(picks, "R64-E1")
    assert cleared == []
    assert unchanged["R32-E1"] == "Duke"
