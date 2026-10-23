"""Template metadata for the 2026 printable March Madness bracket.

The supplied template is a visual bracket, not a data table. This module owns
the one authoritative map from each game to its Excel cell, plus the scoring
rules printed on the sheet.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

# ---------------------------------------------------------------------------
# Scoring (printed on the 2026 sheet)
# ---------------------------------------------------------------------------
ROUND_ORDER: Final[tuple[str, ...]] = ("R64", "R32", "S16", "E8", "F4", "CH")

ROUND_NAMES: Final[dict[str, str]] = {
    "R64": "Round of 64",
    "R32": "Round of 32",
    "S16": "Sweet 16",
    "E8": "Elite Eight",
    "F4": "Final Four",
    "CH": "Championship",
}

ROUND_WEIGHTS: Final[dict[str, int]] = {
    "R64": 1,
    "R32": 2,
    "S16": 4,
    "E8": 6,
    "F4": 8,
    "CH": 12,
}

ROUND_GAME_COUNTS: Final[dict[str, int]] = {
    "R64": 32,
    "R32": 16,
    "S16": 8,
    "E8": 4,
    "F4": 2,
    "CH": 1,
}

ROUND_STANDINGS_HEADERS: Final[dict[str, str]] = {
    "R64": "R64 (×1)",
    "R32": "R32 (×2)",
    "S16": "S16 (×4)",
    "E8": "E8 (×6)",
    "F4": "F4 (×8)",
    "CH": "Championship (×12)",
}

TOTAL_MAX_POINTS: Final[int] = sum(
    ROUND_GAME_COUNTS[round_name] * ROUND_WEIGHTS[round_name]
    for round_name in ROUND_ORDER
)

# ---------------------------------------------------------------------------
# Layout anchors and columns (1-based Excel coordinates)
# ---------------------------------------------------------------------------
TITLE_TEXT: Final[str] = "THE 2026 NCAA MEN'S BASKETBALL TOURNAMENT"
NAME_PREFIX: Final[str] = "NAME:"
CHAMPION_LABEL: Final[str] = "2026 NCAA CHAMPION"

REGION_ORDER: Final[tuple[str, ...]] = ("E", "W", "S", "M")
REGION_NAMES: Final[dict[str, str]] = {
    "E": "East",
    "W": "West",
    "S": "South",
    "M": "Midwest",
}
REGION_LABELS: Final[dict[str, str]] = {
    "E": "EAST",
    "W": "WEST",
    "S": "SOUTH",
    "M": "MIDWEST",
}

# Left regions (East, South) use columns A-C for teams; right regions
# (West, Midwest) are mirrored into O-Q.
TEAM_COLUMNS: Final[dict[str, int]] = {"E": 1, "W": 17, "S": 1, "M": 17}
SEED_COLUMNS: Final[dict[str, int]] = {"E": 3, "W": 15, "S": 3, "M": 15}

LEFT_PICK_COLUMNS: Final[dict[str, int]] = {
    "R64": 4,  # D
    "R32": 5,  # E
    "S16": 6,  # F
    "E8": 7,  # G
}
RIGHT_PICK_COLUMNS: Final[dict[str, int]] = {
    "R64": 14,  # N
    "R32": 13,  # M
    "S16": 12,  # L
    "E8": 11,  # K
}
F4_LEFT_COLUMN: Final[int] = 8  # H
F4_RIGHT_COLUMN: Final[int] = 10  # J
CHAMPION_COLUMN: Final[int] = 9  # I

# Row offsets from the EAST/SOUTH region-label row. The template repeats the
# same vertical rhythm for both halves of the bracket.
ROUND_ROW_OFFSETS: Final[dict[str, tuple[int, ...]]] = {
    "R64": (3, 7, 11, 15, 19, 23, 27, 31),
    "R32": (5, 13, 21, 29),
    "S16": (9, 25),
    "E8": (17,),
}
F4_ROW_OFFSET: Final[int] = 28

# R64 team rows relative to the region label; each game occupies four rows.
R64_TOP_TEAM_OFFSET: Final[int] = 2
R64_BOTTOM_TEAM_OFFSET: Final[int] = 4
R64_GAME_ROW_STRIDE: Final[int] = 4

CANONICAL_ANCHORS: Final[dict[str, int]] = {
    "name_row": 2,
    "name_col": 1,
    "east_row": 6,
    "west_row": 6,
    "south_row": 40,
    "midwest_row": 40,
    "champion_row": 44,
    "champion_col": 9,
}


# ---------------------------------------------------------------------------
# Slots
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Slot:
    """One game in the bracket."""

    id: str
    round: str
    region: str | None
    game: int
    row: int
    col: int
    feeders: tuple[str, ...] = ()
    team_cells: tuple[tuple[int, int], ...] = ()


def _region_side(region: str) -> str:
    return "left" if region in {"E", "S"} else "right"


def build_slots(
    east_row: int,
    south_row: int,
    champion_label_row: int,
) -> tuple[Slot, ...]:
    """Build the 63-slot map from detected template anchors.

    `east_row` and `south_row` are the rows holding the EAST and SOUTH labels.
    `champion_label_row` is the row holding "2026 NCAA CHAMPION"; the champion
    pick cell sits directly above that label.
    """

    slots: list[Slot] = []
    anchor_rows = {"E": east_row, "W": east_row, "S": south_row, "M": south_row}

    for round_name in ("R64", "R32", "S16", "E8"):
        offsets = ROUND_ROW_OFFSETS[round_name]
        for region in REGION_ORDER:
            side = _region_side(region)
            columns = LEFT_PICK_COLUMNS if side == "left" else RIGHT_PICK_COLUMNS
            for index, offset in enumerate(offsets, start=1):
                row = anchor_rows[region] + offset
                slot_id = f"{round_name}-{region}{index}"
                team_cells: tuple[tuple[int, int], ...] = ()
                if round_name == "R64":
                    top_row = (
                        anchor_rows[region]
                        + R64_TOP_TEAM_OFFSET
                        + (index - 1) * R64_GAME_ROW_STRIDE
                    )
                    bottom_row = top_row + 2
                    team_col = TEAM_COLUMNS[region]
                    team_cells = ((top_row, team_col), (bottom_row, team_col))
                slots.append(
                    Slot(
                        id=slot_id,
                        round=round_name,
                        region=region,
                        game=index,
                        row=row,
                        col=columns[round_name],
                        team_cells=team_cells,
                    )
                )

    # Fill in feeder relationships now that every slot ID exists.
    by_id = {slot.id: slot for slot in slots}
    feeder_map: dict[str, tuple[str, ...]] = {}
    for region in REGION_ORDER:
        feeder_map[f"R32-{region}1"] = (f"R64-{region}1", f"R64-{region}2")
        feeder_map[f"R32-{region}2"] = (f"R64-{region}3", f"R64-{region}4")
        feeder_map[f"R32-{region}3"] = (f"R64-{region}5", f"R64-{region}6")
        feeder_map[f"R32-{region}4"] = (f"R64-{region}7", f"R64-{region}8")
        feeder_map[f"S16-{region}1"] = (f"R32-{region}1", f"R32-{region}2")
        feeder_map[f"S16-{region}2"] = (f"R32-{region}3", f"R32-{region}4")
        feeder_map[f"E8-{region}1"] = (f"S16-{region}1", f"S16-{region}2")

    slots = [
        Slot(
            id=slot.id,
            round=slot.round,
            region=slot.region,
            game=slot.game,
            row=slot.row,
            col=slot.col,
            feeders=feeder_map.get(slot.id, ()),
            team_cells=slot.team_cells,
        )
        for slot in slots
        if slot.id in by_id
    ]

    f4_row = east_row + F4_ROW_OFFSET
    champion_row = champion_label_row - 1
    slots.extend(
        [
            Slot(
                id="F4-1",
                round="F4",
                region=None,
                game=1,
                row=f4_row,
                col=F4_LEFT_COLUMN,
                feeders=("E8-E1", "E8-S1"),
            ),
            Slot(
                id="F4-2",
                round="F4",
                region=None,
                game=2,
                row=f4_row,
                col=F4_RIGHT_COLUMN,
                feeders=("E8-W1", "E8-M1"),
            ),
            Slot(
                id="CH",
                round="CH",
                region=None,
                game=1,
                row=champion_row,
                col=CHAMPION_COLUMN,
                feeders=("F4-1", "F4-2"),
            ),
        ]
    )

    _validate_slot_map(slots)
    return tuple(slots)


def _validate_slot_map(slots: list[Slot]) -> None:
    expected_counts = ROUND_GAME_COUNTS
    actual_counts = {round_name: 0 for round_name in ROUND_ORDER}
    for slot in slots:
        actual_counts[slot.round] += 1
    if actual_counts != expected_counts:
        raise ValueError(
            f"Slot map has wrong game counts: {actual_counts}; expected {expected_counts}"
        )
    coordinates = [(slot.row, slot.col) for slot in slots]
    if len(set(coordinates)) != len(coordinates):
        raise ValueError("Slot map contains duplicate cell coordinates")
    ids = [slot.id for slot in slots]
    if len(set(ids)) != len(ids):
        raise ValueError("Slot map contains duplicate slot IDs")
    for slot in slots:
        for feeder in slot.feeders:
            if feeder not in ids:
                raise ValueError(f"Slot {slot.id} references missing feeder {feeder}")


CANONICAL_SLOTS: Final[tuple[Slot, ...]] = build_slots(
    CANONICAL_ANCHORS["east_row"],
    CANONICAL_ANCHORS["south_row"],
    CANONICAL_ANCHORS["champion_row"],
)
SLOTS_BY_ID: Final[dict[str, Slot]] = {slot.id: slot for slot in CANONICAL_SLOTS}
SLOT_IDS: Final[tuple[str, ...]] = tuple(slot.id for slot in CANONICAL_SLOTS)
DOWNSTREAM_BY_ID: Final[dict[str, tuple[str, ...]]] = {
    slot_id: tuple(
        child.id for child in CANONICAL_SLOTS if slot_id in child.feeders
    )
    for slot_id in SLOT_IDS
}


def slot_header(slot_id: str) -> str:
    """The human-readable Picks column header for one slot."""

    slot = SLOTS_BY_ID[slot_id]
    if slot.round == "CH":
        return "Championship"
    if slot.round == "F4":
        return f"F4 Game {slot.game}"
    region = REGION_NAMES[slot.region or ""]
    return f"{slot.round} {region} {slot.game}"


SLOT_HEADERS: Final[dict[str, str]] = {
    slot_id: slot_header(slot_id) for slot_id in SLOT_IDS
}
HEADER_TO_SLOT: Final[dict[str, str]] = {
    header: slot_id for slot_id, header in SLOT_HEADERS.items()
}


# ---------------------------------------------------------------------------
# Team-name normalization
# ---------------------------------------------------------------------------
# Deliberately small and explicit: normalize punctuation/spacing, then apply
# known aliases. No fuzzy matching, so a typo never silently becomes a match
# unless it is listed here.
TEAM_ALIASES: Final[dict[str, str]] = {
    "michgian state": "michigan state",
    "michigan st": "michigan state",
    "michigan state university": "michigan state",
    "uconn": "connecticut",
    "connecticut university": "connecticut",
    "nc state": "north carolina state",
    "north carolina st": "north carolina state",
    "ole miss": "mississippi",
    "pitt": "pittsburgh",
    "miami fl": "miami",
    "miami (fl)": "miami",
    "miami oh": "miami (ohio)",
    "miami (oh)": "miami (ohio)",
    "st marys": "st mary's",
    "saint marys": "saint mary's",
    "saint mary's": "st mary's",
    "kennesaw state": "kennesaw st",
    "tennessee state": "tennessee st",
    "wright st": "wright state",
    "california baptist": "cal baptist",
    "liu": "long island",
    "north dakota state": "n dakota state",
    "nd state": "n dakota state",
    "prairie view": "prairie view a&m",
    "prairie view a and m": "prairie view a&m",
    "ucf": "u central florida",
    "central florida": "u central florida",
}


def normalize_team(value: object) -> str:
    """Return a comparison-ready team name."""
    if value is None:
        return ""
    text = str(value).strip().casefold()
    text = text.replace(".", "")
    text = re.sub(r"\s*&\s*", " and ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return TEAM_ALIASES.get(text, text)


def team_matches(left: object, right: object) -> bool:
    left_key = normalize_team(left)
    right_key = normalize_team(right)
    return bool(left_key) and left_key == right_key


def split_team_label(value: object) -> tuple[str, ...]:
    """Split a play-in label such as ``Texas/ NC State`` into both teams."""
    if value is None:
        return ()
    parts = [part.strip() for part in str(value).split("/") if part.strip()]
    return tuple(parts)


def parse_entrant_name(raw: object, fallback: str) -> str:
    """Extract MATT from ``NAME:______________MATT_______________``."""
    if raw is None:
        return fallback
    text = str(raw).strip()
    if not text:
        return fallback
    if ":" in text:
        text = text.split(":", 1)[1]
    text = text.strip("_ ").strip()
    text = re.sub(r"\s+", " ", text)
    return text or fallback
