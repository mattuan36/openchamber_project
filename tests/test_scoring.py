"""Scoring, pending-state, accuracy, and ranking tests."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from bracket.loader import Bracket, parse_bracket
from bracket.scoring import maximum_points, score_all, score_entrant
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
