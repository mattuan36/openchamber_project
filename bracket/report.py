"""Five-sheet Excel report for the bracket scorekeeper.

Sheets: Picks (participants and picks), Standings (derived), State (visible
metadata), Teams (the 32 first-round matchups), and Corrections (entrant-fix
audit log). No hidden state sheet is used.
"""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.formatting.rule import DataBarRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from .loader import REPORT_TITLE, Dataset, is_generated_report
from .scoring import EntrantScore, TIE_BREAK_DESCRIPTION
from .template import (
    REGION_NAMES,
    ROUND_NAMES,
    ROUND_ORDER,
    ROUND_STANDINGS_HEADERS,
    ROUND_WEIGHTS,
    SLOT_IDS,
    SLOTS_BY_ID,
    TOTAL_MAX_POINTS,
    slot_header,
    team_matches,
)


class ReportError(Exception):
    """A user-facing report-writing problem."""


REPORT_SCHEMA_VERSION = "3"
REPORT_FORMAT_NAME = "2026 March Madness Five-Sheet Report"
RULES_VERSION = "2026.1"
APP_VERSION = "2.1.0"

STATE_FIELDS: tuple[str, ...] = (
    "Report schema version",
    "Created (UTC)",
    "Updated (UTC)",
    "Source folder",
    "Scoring rules version",
    "App version",
    "Report format",
)

CORRECTION_FIELDS: tuple[str, ...] = (
    "Timestamp",
    "Entrant",
    "Source File",
    "Slot",
    "Old Pick",
    "New Pick",
    "Reason",
)

TEAM_FIELDS: tuple[str, ...] = ("Slot", "Region", "Team 1", "Team 2")
TEAM_SEED_FIELDS: tuple[str, ...] = ("Seed 1", "Seed 2")
SEEDED_TEAM_FIELDS: tuple[str, ...] = (
    "Slot",
    "Region",
    "Seed 1",
    "Team 1",
    "Seed 2",
    "Team 2",
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def default_state(
    dataset: Dataset,
    *,
    source_folder: str | Path | None = None,
    created: str | None = None,
    updated: str | None = None,
) -> dict[str, str]:
    """Build the visible State metadata block."""

    now = utc_now_iso()
    folder = (
        str(source_folder)
        if source_folder is not None
        else str(dataset.actual.path.parent)
    )
    return {
        "Report schema version": REPORT_SCHEMA_VERSION,
        "Created (UTC)": created or now,
        "Updated (UTC)": updated or now,
        "Source folder": folder,
        "Scoring rules version": RULES_VERSION,
        "App version": APP_VERSION,
        "Report format": REPORT_FORMAT_NAME,
    }


# Palette: dark, round-coded headers with pale data fills.
ROUND_HEADER_FILLS = {
    "R64": "2F5597",
    "R32": "548235",
    "S16": "BF8F00",
    "E8": "C55A11",
    "F4": "7030A0",
    "CH": "C00000",
}
ROUND_DATA_FILLS = {
    "R64": "EAF1FB",
    "R32": "E2EFDA",
    "S16": "FFF2CC",
    "E8": "FCE4D6",
    "F4": "E4DFEC",
    "CH": "FFE699",
}
WHITE = "FFFFFF"
BLACK = "000000"
DARK_BLUE = "1F4E78"
GREEN_FILL = "C6EFCE"
GREEN_TEXT = "006100"
RED_FILL = "FFC7CE"
RED_TEXT = "9C0006"
PENDING_FILL = "E7E6E6"
PENDING_TEXT = "7F7F7F"
MUTED_TEXT = "595959"

HEADER_FONT = Font(name="Calibri", size=9, bold=True, color=WHITE)
BODY_FONT = Font(name="Calibri", size=9)
BODY_BOLD = Font(name="Calibri", size=9, bold=True)
NOTE_FONT = Font(name="Calibri", size=9, italic=True, color=MUTED_TEXT)

CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT = Alignment(horizontal="left", vertical="center")
LEFT_WRAP = Alignment(horizontal="left", vertical="center", wrap_text=True)

THIN_WHITE = Side(style="thin", color=WHITE)
THICK_BLACK = Side(style="thick", color=BLACK)
THIN_GRAY = Side(style="thin", color="D9D9D9")


def _slot_header(slot_id: str) -> str:
    return slot_header(slot_id)


def _slot_comment(slot_id: str) -> str:
    slot = SLOTS_BY_ID[slot_id]
    if slot.round == "CH":
        return f"Championship ({ROUND_WEIGHTS['CH']} points) at cell I{slot.row}."
    if slot.round == "F4":
        return f"Final Four game {slot.game} ({ROUND_WEIGHTS['F4']} points)."
    region = REGION_NAMES[slot.region or ""]
    return (
        f"{ROUND_NAMES[slot.round]} — {region} game {slot.game} "
        f"({ROUND_WEIGHTS[slot.round]} point"
        f"{'s' if ROUND_WEIGHTS[slot.round] != 1 else ''})."
    )


def _fill(color: str) -> PatternFill:
    return PatternFill("solid", fgColor=color)


def _set_cell(
    cell,
    value,
    *,
    font=BODY_FONT,
    fill: str | None = None,
    alignment=CENTER,
    border: Border | None = None,
    number_format: str | None = None,
) -> None:
    cell.value = value
    cell.font = font
    cell.alignment = alignment
    if fill:
        cell.fill = _fill(fill)
    if border is not None:
        cell.border = border
    if number_format:
        cell.number_format = number_format


def _build_picks_sheet(
    workbook: Workbook, dataset: Dataset, scores: list[EntrantScore]
) -> None:
    sheet = workbook.active
    sheet.title = "Picks"
    sheet.sheet_properties.tabColor = DARK_BLUE
    sheet.sheet_view.showGridLines = False
    sheet.sheet_view.zoomScale = 80

    headers = ["Source File", "Entrant", *(_slot_header(slot_id) for slot_id in SLOT_IDS)]
    for index, label in enumerate(headers, start=1):
        cell = sheet.cell(row=1, column=index, value=label)
        slot_id = SLOT_IDS[index - 3] if index >= 3 else None
        round_name = SLOTS_BY_ID[slot_id].round if slot_id else None
        header_fill = (
            ROUND_HEADER_FILLS[round_name] if round_name else DARK_BLUE
        )
        left_border = THIN_WHITE
        if index == 3:
            left_border = THICK_BLACK
        elif slot_id is not None:
            previous = SLOTS_BY_ID[SLOT_IDS[index - 4]]
            if previous.round != round_name:
                left_border = THICK_BLACK
            elif previous.region != SLOTS_BY_ID[slot_id].region:
                left_border = THIN_WHITE
        cell.font = HEADER_FONT
        cell.fill = _fill(header_fill)
        cell.alignment = CENTER
        cell.border = Border(left=left_border)
        if slot_id is not None:
            cell.comment = Comment(_slot_comment(slot_id), "Scorekeeper")
            cell.comment.width = 260
            cell.comment.height = 55

    sheet.freeze_panes = "C2"
    sheet.row_dimensions[1].height = 46
    sheet.column_dimensions["A"].width = 36
    sheet.column_dimensions["B"].width = 25
    for index in range(3, len(SLOT_IDS) + 3):
        sheet.column_dimensions[get_column_letter(index)].width = 14

    # The actual-results row comes first and is visually separate from entrants.
    actual_row = 2
    _set_cell(
        sheet.cell(row=actual_row, column=1),
        dataset.actual.source_name,
        font=Font(name="Calibri", size=9, bold=True, color=WHITE),
        fill=DARK_BLUE,
        alignment=LEFT_WRAP,
    )
    _set_cell(
        sheet.cell(row=actual_row, column=2),
        f"ACTUAL — {dataset.actual.entrant}",
        font=Font(name="Calibri", size=9, bold=True, color=WHITE),
        fill=DARK_BLUE,
        alignment=LEFT_WRAP,
    )
    for offset, slot_id in enumerate(SLOT_IDS, start=3):
        value = dataset.actual.picks.get(slot_id, "").strip()
        cell = sheet.cell(row=actual_row, column=offset)
        if value:
            _set_cell(
                cell,
                value,
                font=Font(name="Calibri", size=9, bold=True, color=WHITE),
                fill=DARK_BLUE,
            )
        else:
            _set_cell(
                cell,
                None,
                font=Font(name="Calibri", size=9, color=PENDING_TEXT),
                fill=PENDING_FILL,
            )

    # Keep the Picks rows in the same order as Standings (best rank first).
    entrant_brackets = (
        [score.bracket for score in scores] if scores else dataset.entrants
    )
    for row_index, bracket in enumerate(entrant_brackets, start=3):
        _set_cell(
            sheet.cell(row=row_index, column=1),
            bracket.source_name,
            alignment=LEFT_WRAP,
        )
        _set_cell(
            sheet.cell(row=row_index, column=2),
            bracket.entrant,
            font=BODY_BOLD,
            alignment=LEFT_WRAP,
        )
        for offset, slot_id in enumerate(SLOT_IDS, start=3):
            actual_value = dataset.actual.picks.get(slot_id, "").strip()
            pick = bracket.picks.get(slot_id, "").strip()
            cell = sheet.cell(row=row_index, column=offset)
            if not actual_value:
                _set_cell(
                    cell,
                    pick or None,
                    font=Font(name="Calibri", size=9, color=PENDING_TEXT),
                    fill=PENDING_FILL,
                )
            elif pick and team_matches(pick, actual_value):
                _set_cell(
                    cell,
                    pick,
                    font=Font(name="Calibri", size=9, color=GREEN_TEXT),
                    fill=GREEN_FILL,
                )
            else:
                _set_cell(
                    cell,
                    pick or None,
                    font=Font(name="Calibri", size=9, color=RED_TEXT),
                    fill=RED_FILL,
                )
        sheet.row_dimensions[row_index].height = 30

    sheet.row_dimensions[actual_row].height = 30
    last_row = max(2, 2 + len(dataset.entrants))
    last_col = 2 + len(SLOT_IDS)
    sheet.auto_filter.ref = f"A1:{get_column_letter(last_col)}{last_row}"
    sheet.print_title_rows = "1:1"
    sheet.page_setup.orientation = "landscape"
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 0
    sheet.sheet_properties.pageSetUpPr.fitToPage = True
    sheet.print_options.horizontalCentered = True

    note = (
        "Row 2 is the actual-results bracket. Green = correct, "
        "red = incorrect, gray = pending (the actual cell is blank)."
    )
    sheet["A1"].comment = Comment(note, "Scorekeeper")
    sheet["A1"].comment.width = 320
    sheet["A1"].comment.height = 80


def _build_standings_sheet(
    workbook: Workbook, dataset: Dataset, scores: list[EntrantScore]
) -> None:
    sheet = workbook.create_sheet("Standings")
    sheet.sheet_properties.tabColor = "548235"
    sheet.sheet_view.showGridLines = False
    sheet.sheet_view.zoomScale = 90

    headers = [
        "Rank",
        "Entrant",
        "Source File",
        *[ROUND_STANDINGS_HEADERS[round_name] for round_name in ROUND_ORDER],
        "Total",
        "Correct Picks",
        "Pending Games",
        "Accuracy",
    ]
    for index, label in enumerate(headers, start=1):
        cell = sheet.cell(row=1, column=index, value=label)
        cell.font = HEADER_FONT
        cell.fill = _fill(DARK_BLUE)
        cell.alignment = CENTER
        cell.border = Border(bottom=THIN_GRAY)
    sheet.row_dimensions[1].height = 44

    widths = {
        "A": 7,
        "B": 27,
        "C": 36,
        "D": 11,
        "E": 11,
        "F": 11,
        "G": 12,
        "H": 11,
        "I": 17,
        "J": 10,
        "K": 12,
        "L": 12,
        "M": 11,
    }
    for column, width in widths.items():
        sheet.column_dimensions[column].width = width

    if not scores:
        sheet.merge_cells("A2:M2")
        cell = sheet["A2"]
        _set_cell(
            cell,
            "No entrant brackets were found. Add filled bracket workbooks to "
            "the input folder and run again.",
            font=NOTE_FONT,
            alignment=LEFT_WRAP,
        )
        sheet.row_dimensions[2].height = 32
    else:
        for row_index, score in enumerate(scores, start=2):
            rank_fill = {1: "FFD966", 2: "D9E1F2", 3: "F4B183"}.get(score.rank)
            rank_font = BODY_BOLD if score.rank <= 3 else BODY_FONT
            _set_cell(
                sheet.cell(row=row_index, column=1),
                score.rank,
                font=rank_font,
                fill=rank_fill,
            )
            _set_cell(
                sheet.cell(row=row_index, column=2),
                score.entrant,
                font=rank_font,
                alignment=LEFT_WRAP,
            )
            _set_cell(
                sheet.cell(row=row_index, column=3),
                score.source_name,
                alignment=LEFT_WRAP,
            )
            for column, round_name in enumerate(ROUND_ORDER, start=4):
                _set_cell(
                    sheet.cell(row=row_index, column=column),
                    score.round_scores[round_name],
                )
            _set_cell(
                sheet.cell(row=row_index, column=10),
                score.total,
                font=BODY_BOLD,
            )
            _set_cell(
                sheet.cell(row=row_index, column=11),
                score.correct,
            )
            _set_cell(
                sheet.cell(row=row_index, column=12),
                score.pending,
            )
            _set_cell(
                sheet.cell(row=row_index, column=13),
                score.accuracy,
                number_format="0.0%",
            )
            sheet.row_dimensions[row_index].height = 22

        last_row = 1 + len(scores)
        sheet.freeze_panes = "C2"
        sheet.auto_filter.ref = f"A1:M{last_row}"
        sheet.conditional_formatting.add(
            f"J2:J{last_row}",
            DataBarRule(
                start_type="num",
                start_value=0,
                end_type="num",
                end_value=TOTAL_MAX_POINTS,
                color="5B9BD5",
                showValue=True,
            ),
        )

        note_row = last_row + 2
        scoring_note = (
            "Scoring: Round of 64 = 1, Round of 32 = 2, Sweet 16 = 4, "
            "Elite Eight = 6, Final Four = 8, Championship = 12. "
            f"Maximum {TOTAL_MAX_POINTS} points."
        )
        pending_note = (
            "A blank actual result is pending: it awards no points and is "
            "excluded from accuracy. Accuracy = correct picks ÷ decided games "
            "(not ÷ 63)."
        )
        for row_offset, text in enumerate(
            (scoring_note, pending_note, TIE_BREAK_DESCRIPTION)
        ):
            row = note_row + row_offset
            sheet.merge_cells(start_row=row, start_column=1, end_row=row, end_column=13)
            _set_cell(
                sheet.cell(row=row, column=1),
                text,
                font=NOTE_FONT,
                alignment=LEFT_WRAP,
            )
            sheet.row_dimensions[row].height = 30

    sheet.print_title_rows = "1:1"
    sheet.page_setup.orientation = "landscape"
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 0
    sheet.sheet_properties.pageSetUpPr.fitToPage = True
    sheet.print_options.horizontalCentered = True

    sheet["J1"].comment = Comment(
        f"Total points out of {TOTAL_MAX_POINTS}; the bar is scaled to the maximum.",
        "Scorekeeper",
    )
    sheet["M1"].comment = Comment(
        "Correct picks divided by decided games. Pending games are excluded.",
        "Scorekeeper",
    )


def _report_team_pairs(dataset: Dataset) -> dict[str, tuple[str, ...]]:
    if dataset.actual.team_pairs:
        return dict(dataset.actual.team_pairs)
    for entrant in dataset.entrants:
        if entrant.team_pairs:
            return dict(entrant.team_pairs)
    return {}


def _report_team_seeds(dataset: Dataset) -> dict[str, tuple[int, ...]]:
    if dataset.actual.team_seeds:
        return dict(dataset.actual.team_seeds)
    for entrant in dataset.entrants:
        if entrant.team_seeds:
            return dict(entrant.team_seeds)
    return {}


def _complete_seed_pairs(
    team_pairs: dict[str, tuple[str, ...]],
    team_seeds: dict[str, tuple[int, ...]],
) -> bool:
    if not team_seeds:
        return False
    return all(
        len(team_pairs.get(slot_id, ())) >= 2
        and len(team_seeds.get(slot_id, ())) == len(team_pairs[slot_id])
        for slot_id in SLOT_IDS
        if slot_id.startswith("R64-")
    )


def _seeded_team_columns(
    teams: tuple[str, ...], seeds: tuple[int, ...]
) -> tuple[int, str, int, str] | None:
    """Group the expanded teams back into the two printed bracket rows.

    A play-in row has two teams sharing one seed, so the seed change is the
    reliable boundary between the top and bottom printed labels.
    """

    if len(teams) < 2 or len(teams) != len(seeds):
        return None
    split = next(
        (index for index in range(1, len(seeds)) if seeds[index] != seeds[0]),
        len(teams),
    )
    if split >= len(teams):
        return None
    team_one = " / ".join(teams[:split])
    team_two = " / ".join(teams[split:])
    if not team_one or not team_two:
        return None
    return seeds[0], team_one, seeds[split], team_two


def _build_state_sheet(
    workbook: Workbook, state: dict[str, str]
) -> None:
    sheet = workbook.create_sheet("State")
    sheet.sheet_properties.tabColor = "7F7F7F"
    sheet.sheet_view.showGridLines = False
    sheet.sheet_view.zoomScale = 100

    for column, label in enumerate(("Key", "Value"), start=1):
        cell = sheet.cell(row=1, column=column, value=label)
        cell.font = HEADER_FONT
        cell.fill = _fill(DARK_BLUE)
        cell.alignment = CENTER

    values = state or {}
    for row_index, key in enumerate(STATE_FIELDS, start=2):
        _set_cell(
            sheet.cell(row=row_index, column=1, value=key),
            key,
            font=BODY_BOLD,
            alignment=LEFT,
            fill="F2F2F2",
        )
        _set_cell(
            sheet.cell(row=row_index, column=2, value=values.get(key, "")),
            values.get(key, ""),
            alignment=LEFT_WRAP,
        )

    # Any unexpected metadata keys stay visible rather than being discarded.
    for row_index, key in enumerate(
        (key for key in values if key not in STATE_FIELDS), start=2 + len(STATE_FIELDS)
    ):
        _set_cell(
            sheet.cell(row=row_index, column=1, value=key),
            key,
            font=BODY_BOLD,
            alignment=LEFT,
            fill="F2F2F2",
        )
        _set_cell(
            sheet.cell(row=row_index, column=2, value=values[key]),
            values[key],
            alignment=LEFT_WRAP,
        )

    sheet.column_dimensions["A"].width = 28
    sheet.column_dimensions["B"].width = 58
    sheet.freeze_panes = "A2"


def _build_teams_sheet(
    workbook: Workbook, dataset: Dataset
) -> None:
    sheet = workbook.create_sheet("Teams")
    sheet.sheet_properties.tabColor = "2F5597"
    sheet.sheet_view.showGridLines = False
    sheet.sheet_view.zoomScale = 100

    pairs = _report_team_pairs(dataset)
    seeds = _report_team_seeds(dataset)
    seeded = _complete_seed_pairs(pairs, seeds)
    fields = SEEDED_TEAM_FIELDS if seeded else TEAM_FIELDS
    for column, label in enumerate(fields, start=1):
        cell = sheet.cell(row=1, column=column, value=label)
        cell.font = HEADER_FONT
        cell.fill = _fill(DARK_BLUE)
        cell.alignment = CENTER

    row_index = 2
    for slot_id in SLOT_IDS:
        if not slot_id.startswith("R64-"):
            continue
        teams = pairs.get(slot_id, ())
        slot = SLOTS_BY_ID[slot_id]
        if seeded:
            columns = _seeded_team_columns(teams, seeds.get(slot_id, ()))
            if columns is None:
                raise ReportError(
                    f"Could not group the seeded teams for {slot_id} into two "
                    "printed matchup rows."
                )
            seed_one, team_one, seed_two, team_two = columns
        else:
            seed_one = seed_two = None
            team_one = teams[0] if teams else ""
            team_two = " / ".join(teams[1:]) if len(teams) > 1 else ""

        _set_cell(
            sheet.cell(row=row_index, column=1, value=slot_id),
            slot_id,
            font=BODY_BOLD,
        )
        _set_cell(
            sheet.cell(row=row_index, column=2, value=REGION_NAMES[slot.region or ""]),
            REGION_NAMES[slot.region or ""],
            alignment=LEFT,
        )
        if seeded:
            _set_cell(
                sheet.cell(row=row_index, column=3, value=seed_one),
                seed_one,
            )
            _set_cell(
                sheet.cell(row=row_index, column=4, value=team_one),
                team_one,
                alignment=LEFT_WRAP,
            )
            _set_cell(
                sheet.cell(row=row_index, column=5, value=seed_two),
                seed_two,
            )
            _set_cell(
                sheet.cell(row=row_index, column=6, value=team_two),
                team_two,
                alignment=LEFT_WRAP,
            )
        else:
            _set_cell(
                sheet.cell(row=row_index, column=3, value=team_one),
                team_one,
                alignment=LEFT_WRAP,
            )
            _set_cell(
                sheet.cell(row=row_index, column=4, value=team_two),
                team_two,
                alignment=LEFT_WRAP,
            )
        row_index += 1

    if seeded:
        widths = {"A": 12, "B": 14, "C": 8, "D": 30, "E": 8, "F": 30}
        last_column = "F"
    else:
        widths = {"A": 12, "B": 14, "C": 30, "D": 30}
        last_column = "D"
    for column, width in widths.items():
        sheet.column_dimensions[column].width = width
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = f"A1:{last_column}{row_index - 1}"


def _build_corrections_sheet(
    workbook: Workbook, corrections: list[dict[str, str]]
) -> None:
    sheet = workbook.create_sheet("Corrections")
    sheet.sheet_properties.tabColor = "C55A11"
    sheet.sheet_view.showGridLines = False
    sheet.sheet_view.zoomScale = 100

    for column, label in enumerate(CORRECTION_FIELDS, start=1):
        cell = sheet.cell(row=1, column=column, value=label)
        cell.font = HEADER_FONT
        cell.fill = _fill(DARK_BLUE)
        cell.alignment = CENTER

    for row_index, entry in enumerate(corrections, start=2):
        for column, field_name in enumerate(CORRECTION_FIELDS, start=1):
            value = entry.get(field_name, "")
            _set_cell(
                sheet.cell(row=row_index, column=column, value=value),
                value,
                alignment=LEFT_WRAP,
            )
        sheet.row_dimensions[row_index].height = 28

    widths = {"A": 23, "B": 20, "C": 32, "D": 12, "E": 20, "F": 20, "G": 52}
    for column, width in widths.items():
        sheet.column_dimensions[column].width = width
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = f"A1:G{max(1, len(corrections) + 1)}"


def build_report(
    dataset: Dataset,
    scores: list[EntrantScore],
    *,
    state: dict[str, str] | None = None,
    corrections: list[dict[str, str]] | None = None,
) -> Workbook:
    """Build the five-sheet report workbook in memory."""

    workbook = Workbook()
    _build_picks_sheet(workbook, dataset, scores)
    _build_standings_sheet(workbook, dataset, scores)
    _build_state_sheet(workbook, state if state is not None else default_state(dataset))
    _build_teams_sheet(workbook, dataset)
    _build_corrections_sheet(workbook, list(corrections or []))
    workbook.properties.title = REPORT_TITLE
    workbook.properties.creator = "Bracket Scorekeeper"
    workbook.properties.description = (
        "Actual results, entrant picks, standings, visible metadata, "
        "first-round teams, and entrant correction history."
    )
    return workbook


def write_report(
    dataset: Dataset,
    scores: list[EntrantScore],
    output_path: Path,
    *,
    state: dict[str, str] | None = None,
    corrections: list[dict[str, str]] | None = None,
) -> Path:
    """Write the five-sheet report atomically, refusing to overwrite an input."""

    output_path = Path(output_path).resolve()
    input_paths = {path.resolve() for path in dataset.files}
    protected_paths = {path.resolve() for path in dataset.protected_paths}
    if output_path in input_paths or (
        output_path in protected_paths and not is_generated_report(output_path)
    ):
        raise ReportError(
            f"Refusing to overwrite an input file: {output_path}. Choose a "
            "different report path."
        )
    if "results" in output_path.stem.casefold():
        raise ReportError(
            "The report filename must not contain 'results'; that word "
            "identifies the actual-results input during discovery."
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    workbook = build_report(
        dataset,
        scores,
        state=state,
        corrections=corrections,
    )
    temp_name: str | None = None
    try:
        file_descriptor, temp_name = tempfile.mkstemp(
            prefix=f".{output_path.stem}_",
            suffix=".xlsx",
            dir=output_path.parent,
        )
        os.close(file_descriptor)
        workbook.save(temp_name)
        try:
            os.replace(temp_name, output_path)
        except PermissionError as exc:
            raise ReportError(
                f"Cannot replace '{output_path}'. Close it in Excel and try again."
            ) from exc
        temp_name = None
    except ReportError:
        raise
    except Exception as exc:
        raise ReportError(f"Could not write report '{output_path}': {exc}") from exc
    finally:
        workbook.close()
        if temp_name is not None:
            try:
                os.unlink(temp_name)
            except OSError:
                pass

    return output_path
