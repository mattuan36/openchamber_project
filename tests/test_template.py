"""The slot map and name normalization are the authoritative template contract."""

from __future__ import annotations

from collections import Counter

from bracket.template import (
    CANONICAL_ANCHORS,
    CANONICAL_SLOTS,
    CHAMPION_LABEL,
    ROUND_GAME_COUNTS,
    ROUND_ORDER,
    ROUND_WEIGHTS,
    SLOT_IDS,
    SLOTS_BY_ID,
    TEAM_COLUMNS,
    TOTAL_MAX_POINTS,
    build_slots,
    normalize_team,
    parse_entrant_name,
    split_team_label,
    team_matches,
)


def test_round_counts_weights_and_maximum() -> None:
    assert ROUND_ORDER == ("R64", "R32", "S16", "E8", "F4", "CH")
    assert ROUND_GAME_COUNTS == {
        "R64": 32,
        "R32": 16,
        "S16": 8,
        "E8": 4,
        "F4": 2,
        "CH": 1,
    }
    assert sum(ROUND_GAME_COUNTS.values()) == 63
    assert ROUND_WEIGHTS == {
        "R64": 1,
        "R32": 2,
        "S16": 4,
        "E8": 6,
        "F4": 8,
        "CH": 12,
    }
    assert TOTAL_MAX_POINTS == 148


def test_slot_map_has_63_unique_slots_and_coordinates() -> None:
    assert len(CANONICAL_SLOTS) == 63
    assert len(SLOT_IDS) == 63
    assert len(set(SLOT_IDS)) == 63
    coordinates = {(slot.row, slot.col) for slot in CANONICAL_SLOTS}
    assert len(coordinates) == 63
    assert Counter(slot.round for slot in CANONICAL_SLOTS) == ROUND_GAME_COUNTS


def test_canonical_anchor_cells() -> None:
    assert CANONICAL_ANCHORS == {
        "name_row": 2,
        "name_col": 1,
        "east_row": 6,
        "west_row": 6,
        "south_row": 40,
        "midwest_row": 40,
        "champion_row": 44,
        "champion_col": 9,
    }
    assert CHAMPION_LABEL == "2026 NCAA CHAMPION"

    assert SLOTS_BY_ID["R64-E1"].row == 9
    assert SLOTS_BY_ID["R64-E1"].col == 4
    assert SLOTS_BY_ID["R64-W1"].row == 9
    assert SLOTS_BY_ID["R64-W1"].col == 14
    assert SLOTS_BY_ID["R64-S1"].row == 43
    assert SLOTS_BY_ID["R64-S1"].col == 4
    assert SLOTS_BY_ID["R64-M1"].row == 43
    assert SLOTS_BY_ID["R64-M1"].col == 14
    assert SLOTS_BY_ID["E8-E1"].row == 23
    assert SLOTS_BY_ID["E8-E1"].col == 7
    assert SLOTS_BY_ID["F4-1"].row == 34
    assert SLOTS_BY_ID["F4-1"].col == 8
    assert SLOTS_BY_ID["F4-2"].row == 34
    assert SLOTS_BY_ID["F4-2"].col == 10
    assert SLOTS_BY_ID["CH"].row == 43
    assert SLOTS_BY_ID["CH"].col == 9


def test_region_layout_and_team_columns() -> None:
    east = SLOTS_BY_ID["R64-E1"].team_cells
    south = SLOTS_BY_ID["R64-S1"].team_cells
    west = SLOTS_BY_ID["R64-W1"].team_cells
    midwest = SLOTS_BY_ID["R64-M1"].team_cells
    assert east == ((8, 1), (10, 1))
    assert south == ((42, 1), (44, 1))
    assert west == ((8, TEAM_COLUMNS["W"]), (10, TEAM_COLUMNS["W"]))
    assert midwest == ((42, TEAM_COLUMNS["M"]), (44, TEAM_COLUMNS["M"]))


def test_build_slots_requires_all_63_games_and_valid_feeders() -> None:
    slots = build_slots(6, 40, 44)
    assert len(slots) == 63
    by_id = {slot.id: slot for slot in slots}
    assert by_id["F4-1"].feeders == ("E8-E1", "E8-S1")
    assert by_id["F4-2"].feeders == ("E8-W1", "E8-M1")
    assert by_id["CH"].feeders == ("F4-1", "F4-2")
    assert by_id["S16-E1"].feeders == ("R32-E1", "R32-E2")
    assert by_id["R32-E1"].feeders == ("R64-E1", "R64-E2")


def test_team_normalization_is_explicit_and_safe() -> None:
    assert normalize_team("  NC   State ") == "north carolina state"
    assert normalize_team("UConn") == "connecticut"
    assert normalize_team("Miami (OH)") == "miami (ohio)"
    assert normalize_team("Prairie View A&M") == "prairie view a&m"
    assert normalize_team("Prairie View A & M") == "prairie view a&m"
    assert normalize_team("LIU") == "long island"
    assert normalize_team("St. Mary's") == "st mary's"
    assert team_matches("NC State", "North Carolina State")
    assert team_matches("St. Mary's", "Saint Mary's")
    assert not team_matches("Duke", "Duke University")
    assert not team_matches("", "")


def test_split_team_label_and_entrant_name() -> None:
    assert split_team_label("Texas/              NC State") == ("Texas", "NC State")
    assert split_team_label("Prairie View A&M/    Lehigh") == (
        "Prairie View A&M",
        "Lehigh",
    )
    assert split_team_label("") == ()
    assert parse_entrant_name("NAME:______________MATT_______________", "fallback") == "MATT"
    assert parse_entrant_name("  Name:   Alice Smith  ", "fallback") == "Alice Smith"
    assert parse_entrant_name("", "fallback") == "fallback"
    assert parse_entrant_name(None, "fallback") == "fallback"
