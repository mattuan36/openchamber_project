"""Streamlit UI for the 2026 March Madness bracket scorekeeper.

The workbook at ``<data folder>/bracket_report.xlsx`` is the persisted save
file. Its Picks sheet is the source of truth for participants and picks;
Standings is recalculated on every load. Setup reads original bracket files
only to create or rebuild a report.
"""

from __future__ import annotations

import os
from dataclasses import replace
from datetime import datetime
from html import escape
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from bracket.loader import BracketError
from bracket.report import (
    APP_VERSION,
    REPORT_FORMAT_NAME,
    ReportError,
    build_report,
    default_state,
    utc_now_iso,
)
from bracket.scoring import TIE_BREAK_DESCRIPTION, available_picks, score_games
from bracket.store import (
    FolderScan,
    ReportSession,
    build_from_raw,
    load_report,
    scan_folder,
)
from bracket.template import (
    REGION_NAMES,
    REGION_ORDER,
    ROUND_NAMES,
    ROUND_ORDER,
    ROUND_STANDINGS_HEADERS,
    SLOT_IDS,
    SLOTS_BY_ID,
    normalize_team,
    team_matches,
)

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=False)

APP_NAME = os.getenv("APP_NAME", "2026 Bracket Scorekeeper")
DEFAULT_DATA_FOLDER = BASE_DIR / "sample_data" / "demo"
PENDING_LABEL = "— Pending —"

st.set_page_config(
    page_title=APP_NAME,
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .block-container { padding-top: 1.8rem; padding-bottom: 3rem;
                         padding-left: 2rem; padding-right: 2rem;
                         max-width: 1500px; }
      .app-kicker { letter-spacing: .14em; text-transform: uppercase;
                    font-size: .72rem; color: var(--text-color); opacity: .6; }
      .app-title { font-size: 2.0rem; font-weight: 700; letter-spacing: -.02em;
                   margin: .1rem 0 .25rem; }
      .app-subtitle { opacity: .72; margin-bottom: 1.1rem; }
      div[data-testid="stMetric"] { border: 1px solid rgba(128,128,128,.22);
                                    border-radius: .75rem; padding: .7rem .9rem; }
      div[data-testid="stMetricValue"] { font-size: 1.4rem; }
      footer { visibility: hidden; }
      .scorecard { display: flex; flex-wrap: wrap; gap: .35rem; margin: .15rem 0 .85rem; }
      .score-cell { flex: 1 1 5.6rem; min-width: 5.2rem; border-radius: .45rem;
                    padding: .32rem .45rem; border: 1px solid rgba(128,128,128,.28);
                    line-height: 1.2; }
      .score-cell .slot { display: block; font-size: .64rem; letter-spacing: .06em;
                          text-transform: uppercase; opacity: .62; }
      .score-cell .team { display: block; font-size: .78rem; font-weight: 600;
                          overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
      .score-cell.correct { background: rgba(34,197,94,.18);
                            border-color: rgba(34,197,94,.55); }
      .score-cell.incorrect { background: rgba(239,68,68,.16);
                              border-color: rgba(239,68,68,.52); }
      .score-cell.pending { background: rgba(128,128,128,.12);
                            border-color: rgba(128,128,128,.32); opacity: .88; }
      .score-region { margin: .6rem 0 .1rem; font-size: .8rem; font-weight: 700;
                      letter-spacing: .05em; text-transform: uppercase; opacity: .65; }
      .saved-path { font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
                    font-size: .82rem; opacity: .8; overflow-wrap: anywhere; }

      /* Actual-results bracket board */
      :root { --bracket-pitch: 108px; --bracket-gap: 4px; }
      .bracket-region-head { display: flex; justify-content: space-between;
                              align-items: baseline; gap: .4rem; margin: 0 0 .3rem;
                              font-size: .68rem; font-weight: 700;
                              letter-spacing: .07em; text-transform: uppercase;
                              opacity: .72; }
      .bracket-region-head.is-right { flex-direction: row-reverse; }
      .bracket-path { font-size: .56rem; font-weight: 500; letter-spacing: .01em;
                      text-transform: none; opacity: .62; white-space: nowrap; }
      .bracket-round-head { text-align: center; font-size: .62rem;
                            font-weight: 600; letter-spacing: .04em;
                            text-transform: uppercase; opacity: .78;
                            margin: 0 0 .2rem; white-space: nowrap; }
      .bracket-final-head { font-size: .72rem; font-weight: 700; letter-spacing: .09em;
                            text-transform: uppercase; opacity: .7; text-align: center;
                            margin: .15rem 0 .2rem; }
      .bracket-game-label { font-size: .54rem; line-height: 1.1; text-align: center;
                            text-transform: uppercase; letter-spacing: .05em;
                            opacity: .62; margin: 0 0 .1rem; min-height: .6rem;
                            overflow: hidden; text-overflow: ellipsis;
                            white-space: nowrap; }
      [class*="st-key-region_"] { border: 1px solid rgba(128,128,128,.16);
                                  border-radius: .7rem; padding: .4rem .45rem;
                                  background: rgba(128,128,128,.025); }
      [class*="st-key-final_panel"] { border: 1px solid rgba(128,128,128,.18);
                                      border-radius: .75rem; padding: .55rem;
                                      background: rgba(128,128,128,.04);
                                      gap: .3rem !important; }
      [class*="st-key-round_headers_"] div[data-testid="stHorizontalBlock"] {
        height: auto !important;
        min-height: 1.5rem !important;
        max-height: none !important;
        overflow: visible !important;
        align-items: stretch !important;
      }
      [class*="st-key-round_headers_"] div[data-testid="stColumn"],
      [class*="st-key-round_headers_"] div[data-testid="stMarkdown"],
      [class*="st-key-round_headers_"] div[data-testid="stMarkdownContainer"] {
        height: auto !important;
        min-height: 1.5rem !important;
        overflow: visible !important;
      }
      [class*="st-key-roundcol_"] { gap: var(--bracket-gap) !important; }
      [class*="st-key-region_"] div[data-testid="stHorizontalBlock"] {
        gap: var(--bracket-gap) !important;
      }
      [class*="st-key-region_"] div[data-testid="stColumn"] {
        min-width: 0 !important;
        flex: 1 1 0 !important;
      }
      [class*="st-key-align_"] { display: flex !important; align-items: center;
                                 justify-content: center; min-width: 0;
                                 flex-shrink: 0; }
      div[data-testid="stVerticalBlock"][class*="st-key-align_R64"] {
        height: calc(var(--bracket-pitch) - var(--bracket-gap)) !important;
        min-height: calc(var(--bracket-pitch) - var(--bracket-gap)) !important;
        max-height: calc(var(--bracket-pitch) - var(--bracket-gap)) !important;
      }
      div[data-testid="stVerticalBlock"][class*="st-key-align_R32"] {
        height: calc(var(--bracket-pitch) * 2 - var(--bracket-gap)) !important;
        min-height: calc(var(--bracket-pitch) * 2 - var(--bracket-gap)) !important;
        max-height: calc(var(--bracket-pitch) * 2 - var(--bracket-gap)) !important;
      }
      div[data-testid="stVerticalBlock"][class*="st-key-align_S16"] {
        height: calc(var(--bracket-pitch) * 4 - var(--bracket-gap)) !important;
        min-height: calc(var(--bracket-pitch) * 4 - var(--bracket-gap)) !important;
        max-height: calc(var(--bracket-pitch) * 4 - var(--bracket-gap)) !important;
      }
      div[data-testid="stVerticalBlock"][class*="st-key-align_E8"] {
        height: calc(var(--bracket-pitch) * 8 - var(--bracket-gap)) !important;
        min-height: calc(var(--bracket-pitch) * 8 - var(--bracket-gap)) !important;
        max-height: calc(var(--bracket-pitch) * 8 - var(--bracket-gap)) !important;
      }
      [class*="st-key-matchup_"] { border: 1px solid rgba(128,128,128,.25);
                                   border-radius: .5rem;
                                   background: rgba(128,128,128,.045);
                                   padding: .24rem .28rem; gap: .14rem !important;
                                   width: 100%; }
      [class*="st-key-align_"] [class*="st-key-matchup_"] { width: 100%; }
      [class*="st-key-matchup_"] button { min-height: 1.65rem; height: 1.65rem;
                                          padding: 0 .28rem; font-size: .68rem;
                                          line-height: 1.15; }
      [class*="st-key-matchup_"] button p { white-space: nowrap; overflow: hidden;
                                            text-overflow: ellipsis; }
      @media (max-width: 1000px) {
        :root { --bracket-pitch: 94px; }
        [class*="st-key-matchup_"] button { font-size: .62rem; }
        .bracket-path { display: none; }
      }
      @media (max-width: 900px) {
        /* Stack the three panels, but keep each region's round columns. */
        [class*="st-key-actual_bracket"] > div > div[data-testid="stHorizontalBlock"] {
          flex-direction: column !important;
          flex-wrap: nowrap !important;
        }
        [class*="st-key-actual_bracket"] > div > div[data-testid="stHorizontalBlock"] > div {
          width: 100% !important;
          flex: 1 1 100% !important;
        }
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
_STATE_DEFAULTS: dict[str, object] = {
    "workspace": None,
    "scan": None,
    "scan_error": None,
    "scan_folder_for": None,
    "actual_choice": None,
    "saved_report_choice": None,
    "start_mode": "Continue saved report",
    "report_path": str(DEFAULT_DATA_FOLDER / "bracket_report.xlsx"),
    "data_folder": str(DEFAULT_DATA_FOLDER),
    "saved_picks": None,
    "undo_stack": [],
    "last_saved_at": None,
    "save_error": None,
    "save_notice": None,
    "autosave": True,
    "compare_index": 0,
    "confirm_rebuild": False,
    "confirm_reload": False,
    "save_path": "",
    "pending_save_path": None,
    "report_path_sync": None,
    "autoload_report": None,
    "correction_slot": "CH",
    "correction_reason": "",
    "correction_confirmed": False,
}
for _key, _value in _STATE_DEFAULTS.items():
    if _key not in st.session_state:
        st.session_state[_key] = _value


def _workspace() -> ReportSession | None:
    return st.session_state.get("workspace")


def _clear_actual_widgets() -> None:
    # Selector keys are ``actual_<slot>``. Do not touch Setup's ``actual_choice``
    # key, which also starts with this prefix.
    for key in list(st.session_state.keys()):
        text = str(key)
        if text.startswith("actual_") and text.removeprefix("actual_") in SLOTS_BY_ID:
            del st.session_state[key]


def _saved_at_from_disk(path: Path) -> str | None:
    try:
        modified = datetime.fromtimestamp(path.stat().st_mtime).astimezone()
    except OSError:
        return None
    return modified.strftime("%Y-%m-%d %H:%M:%S")


def _install_workspace(
    workspace: ReportSession, *, notice: str | None = None
) -> None:
    st.session_state["workspace"] = workspace
    st.session_state["saved_picks"] = dict(workspace.actual.picks)
    st.session_state["undo_stack"] = []
    st.session_state["save_error"] = None
    st.session_state["save_notice"] = notice
    # Show the report's actual on-disk save time, not the time it was loaded.
    st.session_state["last_saved_at"] = _saved_at_from_disk(workspace.report_path)
    st.session_state["pending_save_path"] = str(workspace.report_path)
    st.session_state["report_path_sync"] = str(workspace.report_path)
    st.session_state["compare_index"] = 0
    st.session_state["scan"] = None
    _clear_actual_widgets()


def _record_saved(workspace: ReportSession, message: str) -> None:
    st.session_state["workspace"] = workspace
    st.session_state["saved_picks"] = dict(workspace.actual.picks)
    st.session_state["last_saved_at"] = datetime.now().astimezone().strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    st.session_state["save_error"] = None
    st.session_state["save_notice"] = message
    st.session_state["report_path_sync"] = str(workspace.report_path)
    # The folder now contains a report; let Setup rescan on its next visit.
    st.session_state["scan"] = None


def _save_workspace(
    workspace: ReportSession, *, path: Path | None = None, label: str = "Saved"
) -> bool:
    try:
        saved_path = workspace.save(path)
    except (ReportError, OSError) as exc:
        st.session_state["workspace"] = workspace
        st.session_state["save_error"] = str(exc)
        st.session_state["save_notice"] = None
        return False
    _record_saved(workspace, f"{label} {saved_path.name}")
    st.session_state["pending_save_path"] = str(saved_path)
    return True


def _push_undo(workspace: ReportSession, label: str) -> None:
    stack = list(st.session_state.get("undo_stack", []))
    stack.append({"picks": dict(workspace.actual.picks), "label": label})
    st.session_state["undo_stack"] = stack[-25:]


def _handle_team_pick(slot_id: str, team: str) -> None:
    """Set a winner, or clear the game when the winner is clicked again."""

    workspace = _workspace()
    if workspace is None:
        return
    current = workspace.actual.picks.get(slot_id, "").strip()
    value = "" if current and team_matches(current, team) else team
    if value == current:
        return

    _push_undo(workspace, f"{slot_id}: {value or 'Pending'}")
    updated, cleared = workspace.with_actual_pick(slot_id, value)
    st.session_state["workspace"] = updated
    st.session_state["save_notice"] = None
    notice = (
        f"Set {slot_id} to {value}."
        if value
        else f"Cleared {slot_id} back to pending."
    )
    if cleared:
        notice += (
            " Cleared downstream pick"
            + ("s" if len(cleared) > 1 else "")
            + ": "
            + ", ".join(cleared)
            + "."
        )
    if st.session_state.get("autosave", True):
        if not _save_workspace(updated, label="Autosaved"):
            return
        notice = f"Autosaved. {notice}"
    st.session_state["save_notice"] = notice


def _folder_scan(folder_text: str) -> FolderScan | None:
    folder = Path(folder_text).expanduser()
    cached = st.session_state.get("scan")
    try:
        resolved = folder.resolve()
    except OSError:
        resolved = folder
    if cached is not None and cached.folder == resolved:
        return cached
    try:
        scan = scan_folder(folder)
    except (BracketError, OSError) as exc:
        st.session_state["scan"] = None
        st.session_state["scan_error"] = str(exc)
        return None
    st.session_state["scan"] = scan
    st.session_state["scan_error"] = None
    if st.session_state.get("scan_folder_for") != str(scan.folder):
        st.session_state["report_path"] = str(scan.default_report)
        st.session_state["scan_folder_for"] = str(scan.folder)
        st.session_state["actual_choice"] = None
        st.session_state["saved_report_choice"] = None
        # A path remembered from the previous folder must not override the
        # new folder's default report path.
        st.session_state["report_path_sync"] = None
    return scan


def _all_warnings(workspace: ReportSession) -> list[str]:
    messages = list(workspace.warnings)
    messages.extend(workspace.actual.warnings)
    for entrant in workspace.entrants:
        messages.extend(
            f"{entrant.source_name}: {warning}" for warning in entrant.warnings
        )
    return list(dict.fromkeys(message for message in messages if message))


def _selected_actual_file(scan: FolderScan) -> Path | None:
    names = [path.name for path in scan.raw_files]
    if not names:
        return None
    selected = st.session_state.get("actual_choice")
    if selected not in names:
        default_index = next(
            (
                index
                for index, path in enumerate(scan.raw_files)
                if "results" in path.stem.casefold()
            ),
            0,
        )
        selected = names[default_index]
        st.session_state["actual_choice"] = selected
    return next(path for path in scan.raw_files if path.name == selected)


def _render_warnings(workspace: ReportSession) -> None:
    warnings = _all_warnings(workspace)
    if not warnings:
        st.success("Validation passed with no warnings.", icon="✅")
        return
    with st.expander(f"Validation warnings ({len(warnings)})", expanded=True):
        for message in warnings:
            st.warning(message, icon="⚠️")


def _render_setup() -> None:
    st.header("Setup")
    st.caption(
        "Choose a local folder containing bracket files. Reports are written "
        "to the same folder by default and become the saved state."
    )

    folder_text = st.text_input(
        "Data folder",
        key="data_folder",
        persist_state="session",
        help="A local folder. It is scanned non-recursively for .xlsx, .xlsm, and .csv.",
    )
    scan = _folder_scan(folder_text)

    # Keep the editable Setup path in step with saves, Save As, and reports
    # opened from another page.
    path_sync = st.session_state.get("report_path_sync")
    if path_sync:
        st.session_state["report_path"] = path_sync
        st.session_state["report_path_sync"] = None

    report_text = st.text_input(
        "Report path",
        key="report_path",
        persist_state="session",
        help="The saved report. Names containing 'results' are rejected.",
    )

    left, right = st.columns([1, 1])
    with left:
        if st.button("Rescan folder", key="rescan_folder", width="stretch"):
            # Refresh the scan without discarding the typed report path or
            # the selected actual-results file.
            st.session_state["scan"] = None
            st.rerun()
    with right:
        st.caption(
            "Report filenames may not contain 'results'. Raw bracket files are "
            "never overwritten."
        )

    if scan is None:
        st.error(st.session_state.get("scan_error") or "The folder could not be scanned.")
        return

    metrics = st.columns(4)
    metrics[0].metric("Raw bracket files", len(scan.raw_files))
    metrics[1].metric("Saved reports", len(scan.reports))
    metrics[2].metric("Actual candidates", len(scan.actual_candidates))
    metrics[3].metric("Report", Path(report_text).name or "—")

    saved_workspace = _workspace()
    if scan.reports:
        report_names = [path.name for path in scan.reports]
        if st.session_state.get("saved_report_choice") not in report_names:
            default_report = (
                scan.default_report
                if scan.default_report in scan.reports
                else scan.reports[0]
            )
            st.session_state["saved_report_choice"] = default_report.name
        st.radio(
            "Start from",
            ["Continue saved report", "Rebuild from original bracket files"],
            key="start_mode",
            horizontal=True,
        )
    else:
        st.info(
            "No saved report found in this folder. Create one from the original "
            "bracket files below.",
            icon="📄",
        )

    mode = st.session_state.get("start_mode", "Continue saved report")
    if scan.reports and mode == "Continue saved report":
        report_name = st.selectbox(
            "Saved report",
            [path.name for path in scan.reports],
            key="saved_report_choice",
        )
        report_file = next(path for path in scan.reports if path.name == report_name)
        st.caption(f"Opening: `{report_file}`")
        report_is_open = (
            saved_workspace is not None
            and saved_workspace.report_path.resolve() == report_file.resolve()
        )

        # Continuing the saved report is the default. On a fresh session, load
        # it without an extra click; the rebuild option below still replaces it.
        if (
            saved_workspace is None
            and st.session_state.get("autoload_report") != str(report_file)
        ):
            st.session_state["autoload_report"] = str(report_file)
            try:
                workspace = load_report(report_file)
            except ReportError as exc:
                st.error(str(exc))
            else:
                _install_workspace(workspace, notice="Saved report loaded.")
                st.rerun()

        label = "Reload saved report" if report_is_open else "Open saved report"
        if st.button(label, key="open_saved_report", type="primary"):
            try:
                workspace = load_report(report_file)
            except ReportError as exc:
                st.error(str(exc))
            else:
                _install_workspace(workspace, notice="Saved report loaded.")
                st.rerun()
    else:
        if not scan.raw_files:
            st.warning(
                "This folder has no raw bracket files, so a report cannot be "
                "rebuilt here. Continue the saved report instead.",
                icon="📄",
            )
            return
        if not scan.actual_candidates:
            st.warning(
                "No raw filename contains 'results'. Choose the actual-results "
                "file explicitly before creating the report.",
                icon="📄",
            )
        elif len(scan.actual_candidates) > 1:
            st.warning(
                "More than one raw filename contains 'results'. Choose the "
                "official actual-results file explicitly.",
                icon="📄",
            )

        actual_file = _selected_actual_file(scan)
        actual_name = st.selectbox(
            "Actual-results file",
            [path.name for path in scan.raw_files],
            key="actual_choice",
            help=(
                "Auto-selected by 'results' in the filename. Override it if the "
                "official results use a different name."
            ),
        )
        actual_file = next(path for path in scan.raw_files if path.name == actual_name)
        st.caption(
            f"Entrants will be built from the other {len(scan.raw_files) - 1} "
            f"raw file(s). Actual: `{actual_file.name}`"
        )
        confirm = st.checkbox(
            "Replace any saved edits in the report at this path",
            key="setup_confirm_rebuild",
            value=not scan.reports,
        )
        if st.button(
            "Rebuild from original bracket files"
            if scan.reports
            else "Create report from brackets",
            key="create_report",
            type="primary",
            disabled=not confirm,
        ):
            try:
                workspace = build_from_raw(
                    scan.folder,
                    actual_path=actual_file,
                    report_path=Path(report_text),
                )
            except (BracketError, ReportError, OSError) as exc:
                st.error(str(exc))
            else:
                _install_workspace(workspace)
                _save_workspace(workspace, label="Report created")
                st.rerun()

    workspace = _workspace()
    if workspace is not None:
        st.divider()
        st.subheader("Current report")
        cards = st.columns(4)
        cards[0].metric("Entrants", len(workspace.entrants))
        cards[1].metric("Pending games", workspace.pending)
        cards[2].metric("Corrections", len(workspace.corrections))
        cards[3].metric(
            "Source folder",
            Path(workspace.source_folder or workspace.report_path.parent).name,
        )
        st.markdown(
            f'<p class="saved-path">{escape(str(workspace.report_path))}</p>',
            unsafe_allow_html=True,
        )
        state_cards = st.columns(3)
        state_cards[0].metric(
            "Schema", workspace.state.get("Report schema version", "—")
        )
        state_cards[1].metric(
            "Rules", workspace.state.get("Scoring rules version", "—")
        )
        state_cards[2].metric("App", workspace.state.get("App version", APP_VERSION))
        _render_warnings(workspace)
    elif saved_workspace is not None:
        st.caption(
            f"Currently editing `{saved_workspace.report_path}` from another folder. "
            "Create or open a report here to switch."
        )


# ---------------------------------------------------------------------------
# Actual Results
# ---------------------------------------------------------------------------
def _format_pick(value: str) -> str:
    return value if value else PENDING_LABEL


def _seed_label(team: str, seed_map: dict[str, int]) -> str:
    seed = seed_map.get(normalize_team(team))
    return f"{seed} · {team}" if seed else team


def _matchup_options(slot_id: str, workspace: ReportSession) -> list[str]:
    options: list[str] = []
    for team in available_picks(slot_id, workspace.team_pairs, workspace.actual.picks):
        if team and not any(team_matches(team, existing) for existing in options):
            options.append(team)
    current = workspace.actual.picks.get(slot_id, "").strip()
    if current and not any(team_matches(current, existing) for existing in options):
        options.append(current)
    return options


def _region_slots(region: str, round_name: str) -> list[str]:
    return [
        slot_id
        for slot_id in SLOT_IDS
        if SLOTS_BY_ID[slot_id].region == region
        and SLOTS_BY_ID[slot_id].round == round_name
    ]


def _matchup_card(
    slot_id: str,
    workspace: ReportSession,
    seed_map: dict[str, int],
    *,
    label: str | None = None,
) -> None:
    slot = SLOTS_BY_ID[slot_id]
    current = workspace.actual.picks.get(slot_id, "").strip()
    options = _matchup_options(slot_id, workspace)
    card_label = label or f"Game {slot.game}"
    if len(options) > 2:
        card_label += " · Play-in"

    with st.container(key=f"matchup_{slot_id}"):
        st.markdown(
            f'<div class="bracket-game-label">{escape(card_label)}</div>',
            unsafe_allow_html=True,
        )
        if not options:
            st.button(
                PENDING_LABEL,
                key=f"pick_{slot_id}_pending",
                disabled=True,
                width="stretch",
            )
            return
        for index, team in enumerate(options):
            selected = bool(current and team_matches(current, team))
            st.button(
                _seed_label(team, seed_map),
                key=f"pick_{slot_id}_{index}",
                type="primary" if selected else "secondary",
                icon=":material/check:" if selected else None,
                help=(
                    "Click again to clear this winner."
                    if selected
                    else f"Pick {team} as the actual winner."
                ),
                on_click=_handle_team_pick,
                args=(slot_id, team),
                disabled=not workspace.teams_complete,
                width="stretch",
            )


def _render_region_board(
    region: str,
    workspace: ReportSession,
    seed_map: dict[str, int],
    *,
    mirrored: bool = False,
) -> None:
    rounds = ("E8", "S16", "R32", "R64") if mirrored else ("R64", "R32", "S16", "E8")
    path = "E8 ← S16 ← R32 ← R64" if mirrored else "R64 → R32 → S16 → E8"
    header_class = "bracket-region-head is-right" if mirrored else "bracket-region-head"
    with st.container(key=f"region_{region}"):
        st.markdown(
            f'<div class="{header_class}"><span>{escape(REGION_NAMES[region])}</span>'
            f'<span class="bracket-path">{path}</span></div>',
            unsafe_allow_html=True,
        )
        with st.container(key=f"round_headers_{region}", gap=None):
            header_columns = st.columns(4, gap="small", wrap=False)
            for column, round_name in zip(header_columns, rounds):
                with column:
                    st.markdown(
                        f'<div class="bracket-round-head">'
                        f"{ROUND_STANDINGS_HEADERS[round_name]}</div>",
                        unsafe_allow_html=True,
                    )
        grid_columns = st.columns(4, gap="small", wrap=False)
        for column, round_name in zip(grid_columns, rounds):
            with column:
                with st.container(
                    key=f"roundcol_{region}_{round_name}", gap=None
                ):
                    for slot_id in _region_slots(region, round_name):
                        with st.container(key=f"align_{slot_id}", gap=None):
                            _matchup_card(slot_id, workspace, seed_map)


def _render_final_board(
    workspace: ReportSession, seed_map: dict[str, int]
) -> None:
    with st.container(key="final_panel"):
        st.markdown(
            '<div class="bracket-final-head">Final Four</div>',
            unsafe_allow_html=True,
        )
        _matchup_card(
            "F4-1",
            workspace,
            seed_map,
            label="F4 Game 1 · East / South",
        )
        _matchup_card(
            "F4-2",
            workspace,
            seed_map,
            label="F4 Game 2 · West / Midwest",
        )
        st.markdown(
            '<div class="bracket-final-head">Championship</div>',
            unsafe_allow_html=True,
        )
        _matchup_card(
            "CH",
            workspace,
            seed_map,
            label="National championship",
        )


def _round_groups(round_name: str) -> list[tuple[str | None, list[str]]]:
    slot_ids = [slot_id for slot_id in SLOT_IDS if SLOTS_BY_ID[slot_id].round == round_name]
    if round_name in {"F4", "CH"}:
        return [(None, slot_ids)]
    return [
        (region, [slot_id for slot_id in slot_ids if SLOTS_BY_ID[slot_id].region == region])
        for region in REGION_ORDER
    ]


def _render_actual_results() -> None:
    workspace = _workspace()
    if workspace is None:
        st.info("Load or create a report on the Setup page first.", icon="🏀")
        return

    st.header("Actual Results")
    st.caption(
        "Click a team to set the actual winner for that game. The winner is "
        "highlighted; click it again to return the game to pending. A pending "
        "game awards no points and is excluded from accuracy."
    )
    if not workspace.teams_complete:
        st.warning(
            "This legacy report has no first-round team data. It is read-only; "
            "rebuild it from the original bracket files before editing or saving.",
            icon="📄",
        )
    elif not workspace.team_seeds_complete:
        st.info(
            "This saved report has no seed data. Rebuild it from the original "
            "bracket files to show seeds beside the team names.",
            icon="🌱",
        )

    filled = len(SLOT_IDS) - workspace.pending
    cards = st.columns(4)
    cards[0].metric("Actual source", workspace.actual.source_name)
    cards[1].metric("Decided games", f"{filled} / {len(SLOT_IDS)}")
    cards[2].metric("Pending games", workspace.pending)
    cards[3].metric(
        "Autosave", "On" if st.session_state.get("autosave", True) else "Off"
    )
    if st.session_state.get("save_error"):
        st.error(st.session_state["save_error"], icon="💾")
    elif st.session_state.get("save_notice"):
        st.success(st.session_state["save_notice"], icon="💾")
    if st.session_state.get("last_saved_at"):
        st.caption(f"Saved at: {st.session_state['last_saved_at']}")

    actions = st.columns([1, 1, 2])
    undo_stack = st.session_state.get("undo_stack", [])
    with actions[0]:
        if st.button(
            "Undo last change",
            key="undo_actual",
            disabled=not undo_stack,
            width="stretch",
        ):
            entry = undo_stack.pop()
            workspace = replace(
                workspace,
                actual=replace(workspace.actual, picks=entry["picks"]),
                _dataset=None,
            )
            st.session_state["workspace"] = workspace
            st.session_state["undo_stack"] = undo_stack
            _clear_actual_widgets()
            st.session_state["save_notice"] = f"Undid {entry['label']}"
            if st.session_state.get("autosave", True):
                _save_workspace(workspace, label="Autosaved after undo")
            st.rerun()
    with actions[1]:
        saved_picks = st.session_state.get("saved_picks")
        reset_disabled = saved_picks is None or saved_picks == workspace.actual.picks
        if st.button(
            "Reset to saved",
            key="reset_actual",
            disabled=reset_disabled,
            width="stretch",
        ):
            _push_undo(workspace, "reset to saved")
            workspace = replace(
                workspace,
                actual=replace(workspace.actual, picks=dict(saved_picks)),
                _dataset=None,
            )
            st.session_state["workspace"] = workspace
            _clear_actual_widgets()
            st.session_state["save_notice"] = "Restored the saved actual results."
            if st.session_state.get("autosave", True):
                _save_workspace(workspace, label="Autosaved after reset")
            st.rerun()
    with actions[2]:
        st.caption(
            "Changing a feeder winner clears downstream picks that are no longer "
            "possible."
        )

    seed_map = workspace.team_seed_map
    with st.container(key="actual_bracket"):
        left, center, right = st.columns(
            [5, 2.2, 5], gap="small", vertical_alignment="top", wrap=False
        )
        with left:
            _render_region_board("E", workspace, seed_map)
            _render_region_board("S", workspace, seed_map)
        with center:
            _render_final_board(workspace, seed_map)
        with right:
            _render_region_board("W", workspace, seed_map, mirrored=True)
            _render_region_board("M", workspace, seed_map, mirrored=True)


# ---------------------------------------------------------------------------
# Leaderboard
# ---------------------------------------------------------------------------
def _scores_frame(scores) -> pd.DataFrame:
    rows = []
    for score in scores:
        row = {
            "Rank": score.rank,
            "Entrant": score.entrant,
            "Source File": score.source_name,
        }
        for round_name in ROUND_ORDER:
            row[ROUND_STANDINGS_HEADERS[round_name]] = score.round_scores[round_name]
        row.update(
            {
                "Total": score.total,
                "Correct Picks": score.correct,
                "Pending Games": score.pending,
                "Accuracy": score.accuracy,
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def _render_leaderboard() -> None:
    workspace = _workspace()
    if workspace is None:
        st.info("Load or create a report on the Setup page first.", icon="🏀")
        return

    scores = workspace.scores
    st.header("Leaderboard")
    if not scores:
        st.warning("This report has no entrants yet.", icon="👥")
        return

    leader = scores[0]
    cards = st.columns(4)
    cards[0].metric("Leader", leader.entrant)
    cards[1].metric("Top score", f"{leader.total} / 148")
    cards[2].metric("Entrants", len(scores))
    cards[3].metric("Pending games", workspace.pending)

    frame = _scores_frame(scores)
    display = frame.copy()
    display["Accuracy"] = display["Accuracy"].map(lambda value: f"{value:.1%}")
    st.dataframe(display, hide_index=True, width="stretch")

    chart = pd.DataFrame(
        {
            "Entrant": [score.entrant for score in scores],
            "Total": [score.total for score in scores],
        }
    ).set_index("Entrant")
    st.bar_chart(chart, height=340, horizontal=True, sort=False)

    st.caption(TIE_BREAK_DESCRIPTION)
    st.download_button(
        "Download standings CSV",
        data=frame.to_csv(index=False).encode("utf-8"),
        file_name="standings.csv",
        mime="text/csv",
        width="stretch",
    )


# ---------------------------------------------------------------------------
# Compare
# ---------------------------------------------------------------------------
def _scorecard_html(actual, entrant) -> str:
    results = {result.slot_id: result for result in score_games(actual, entrant)}
    blocks: list[str] = []
    for round_name in ROUND_ORDER:
        blocks.append(
            f'<div class="score-region">{escape(ROUND_NAMES[round_name])}</div>'
        )
        for region, slot_ids in _round_groups(round_name):
            if region is not None:
                blocks.append(
                    f'<div class="score-region">{escape(REGION_NAMES[region])}</div>'
                )
            blocks.append('<div class="scorecard">')
            for slot_id in slot_ids:
                result = results[slot_id]
                slot = SLOTS_BY_ID[slot_id]
                badge = (
                    "CH"
                    if slot.round == "CH"
                    else f"F4-{slot.game}"
                    if slot.round == "F4"
                    else f"{slot.region}{slot.game}"
                )
                pick = result.pick or "—"
                title = (
                    f"{slot_id} | Actual: {result.actual or 'Pending'} | "
                    f"Pick: {result.pick or 'Blank'} | "
                    f"{result.status.title()} | {result.points} pts"
                )
                blocks.append(
                    f'<div class="score-cell {result.status}" title="{escape(title)}">'
                    f'<span class="slot">{escape(badge)}</span>'
                    f'<span class="team">{escape(pick)}</span></div>'
                )
            blocks.append("</div>")
    return "\n".join(blocks)


def _render_compare() -> None:
    workspace = _workspace()
    if workspace is None:
        st.info("Load or create a report on the Setup page first.", icon="🏀")
        return

    scores = workspace.scores
    st.header("Compare")
    if not scores:
        st.warning("This report has no entrants yet.", icon="👥")
        return

    if st.session_state.get("compare_index", 0) >= len(scores):
        st.session_state["compare_index"] = 0
    selected_index = st.selectbox(
        "Entrant",
        list(range(len(scores))),
        key="compare_index",
        format_func=lambda index: (
            f"{scores[index].entrant} — {scores[index].source_name}"
        ),
    )
    score = scores[selected_index]
    entrant = score.bracket
    results = score_games(workspace.actual, entrant)

    cards = st.columns(5)
    cards[0].metric("Total", f"{score.total} / 148")
    cards[1].metric("Rank", f"#{score.rank}")
    cards[2].metric("Correct picks", f"{score.correct} / {score.decided}")
    cards[3].metric("Pending games", score.pending)
    cards[4].metric("Accuracy", f"{score.accuracy:.1%}")

    round_frame = pd.DataFrame(
        {
            "Round": [ROUND_NAMES[round_name] for round_name in ROUND_ORDER],
            "Points": [score.round_scores[round_name] for round_name in ROUND_ORDER],
        }
    ).set_index("Round")
    st.subheader("Round-by-round points")
    st.bar_chart(round_frame, height=280, sort=False)

    st.subheader("Scorecard")
    st.caption(
        "Green = correct · Red = incorrect · Gray = pending actual result. "
        "Hover or tap a game for the actual winner and points."
    )
    st.markdown(
        f'<div>{_scorecard_html(workspace.actual, entrant)}</div>',
        unsafe_allow_html=True,
    )

    detail_rows = []
    for result in results:
        slot = SLOTS_BY_ID[result.slot_id]
        detail_rows.append(
            {
                "Slot": result.slot_id,
                "Round": ROUND_NAMES[result.round],
                "Region": REGION_NAMES.get(slot.region or "", "Final"),
                "Actual Pick": result.actual,
                "Entrant Pick": result.pick,
                "Result": result.status.title(),
                "Points": result.points,
            }
        )
    detail = pd.DataFrame(detail_rows)
    with st.expander("All 63 games", expanded=False):
        st.dataframe(detail, hide_index=True, width="stretch")

    misses = [result for result in results if result.status == "incorrect"]
    misses.sort(key=lambda result: (-result.weight, ROUND_ORDER.index(result.round)))
    st.subheader("Biggest misses")
    if misses:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Slot": result.slot_id,
                        "Round": ROUND_NAMES[result.round],
                        "Actual Pick": result.actual,
                        "Entrant Pick": result.pick or "(blank)",
                        "Points Missed": result.weight,
                    }
                    for result in misses[:10]
                ]
            ),
            hide_index=True,
            width="stretch",
        )
    else:
        st.caption("No misses yet — every decided game is correct.")

    leader = scores[0]
    leader_results = {
        result.slot_id: result for result in score_games(workspace.actual, leader.bracket)
    }
    selected_results = {result.slot_id: result for result in results}
    leader_only = [
        leader_results[slot_id]
        for slot_id in SLOT_IDS
        if leader_results[slot_id].status == "correct"
        and selected_results[slot_id].status != "correct"
    ]
    st.subheader("Leader scored, this entrant did not")
    if leader.entrant == score.entrant and leader.source_name == score.source_name:
        st.caption("This entrant is the leader.")
    elif leader_only:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Slot": result.slot_id,
                        "Round": ROUND_NAMES[result.round],
                        "Actual Pick": result.actual,
                        "Leader Pick": result.pick,
                        "Entrant Pick": selected_results[result.slot_id].pick
                        or "(blank)",
                        "Points": result.weight,
                    }
                    for result in leader_only[:15]
                ]
            ),
            hide_index=True,
            width="stretch",
        )
    else:
        st.caption("The leader did not score on any game this entrant missed.")

    # Entrant picks are intentionally locked behind this advanced control.
    st.divider()
    with st.expander("Advanced: correct an entrant pick", expanded=False):
        st.warning(
            "Entrant picks are normally read-only. A correction requires a reason "
            "and explicit confirmation and is written to the Corrections sheet.",
            icon="🔒",
        )
        if not workspace.teams_complete:
            st.warning(
                "Rebuild this legacy report from the original bracket files before "
                "correcting entrant picks.",
                icon="📄",
            )
        slot_options = SLOT_IDS
        correction_slot = st.selectbox(
            "Game to correct",
            slot_options,
            key="correction_slot",
            format_func=lambda slot_id: f"{slot_id} — {SLOT_STANDINGS_LABEL[slot_id]}",
        )
        current_pick = entrant.picks.get(correction_slot, "").strip()
        options: list[str] = [""]
        for team in available_picks(
            correction_slot, workspace.team_pairs, entrant.picks
        ):
            if team and not any(team_matches(team, existing) for existing in options):
                options.append(team)
        if current_pick and current_pick not in options:
            options.append(current_pick)
        if st.session_state.get("correction_new_pick") not in options:
            st.session_state.pop("correction_new_pick", None)
        new_pick = st.selectbox(
            "Corrected pick",
            options,
            index=options.index(current_pick) if current_pick in options else 0,
            format_func=_format_pick,
            key="correction_new_pick",
        )
        reason = st.text_input(
            "Reason",
            key="correction_reason",
            placeholder="For example: misread the handwritten bracket",
        )
        confirmed = st.checkbox(
            "I understand this changes saved entrant picks and is permanently logged",
            key="correction_confirmed",
        )
        if st.button(
            "Apply correction",
            key="apply_correction",
            type="primary",
            disabled=(
                not reason.strip()
                or not confirmed
                or not workspace.teams_complete
            ),
        ):
            try:
                updated, entry = workspace.with_corrected_entrant(
                    selected_index,
                    correction_slot,
                    new_pick,
                    reason,
                )
            except ReportError as exc:
                st.error(str(exc))
            else:
                st.session_state["workspace"] = updated
                st.session_state["save_notice"] = (
                    f"Corrected {entry['Entrant']} {entry['Slot']}."
                )
                if st.session_state.get("autosave", True):
                    _save_workspace(updated, label="Autosaved correction")
                st.rerun()


SLOT_STANDINGS_LABEL = {
    slot_id: (
        "Championship"
        if slot_id == "CH"
        else f"F4 Game {SLOTS_BY_ID[slot_id].game}"
        if slot_id.startswith("F4-")
        else f"{SLOTS_BY_ID[slot_id].round} "
        f"{REGION_NAMES.get(SLOTS_BY_ID[slot_id].region or '', '')} "
        f"{SLOTS_BY_ID[slot_id].game}"
    )
    for slot_id in SLOT_IDS
}


# ---------------------------------------------------------------------------
# Save / Load
# ---------------------------------------------------------------------------
def _report_bytes(workspace: ReportSession) -> bytes:
    state = dict(workspace.state)
    state.update(default_state(workspace.dataset, source_folder=workspace.source_folder))
    state["Created (UTC)"] = workspace.state.get("Created (UTC)", state["Created (UTC)"])
    state["Updated (UTC)"] = utc_now_iso()
    workbook = build_report(
        workspace.dataset,
        workspace.scores,
        state=state,
        corrections=workspace.corrections,
    )
    buffer = BytesIO()
    try:
        workbook.save(buffer)
    finally:
        workbook.close()
    return buffer.getvalue()


def _render_save_load() -> None:
    workspace = _workspace()
    if workspace is None:
        st.info("Load or create a report on the Setup page first.", icon="🏀")
        return

    st.header("Save / Load")
    st.markdown(
        f'<p class="saved-path">{escape(str(workspace.report_path))}</p>',
        unsafe_allow_html=True,
    )
    pending_save_path = st.session_state.get("pending_save_path")
    if pending_save_path:
        st.session_state["save_path"] = pending_save_path
        st.session_state["pending_save_path"] = None
    can_write = workspace.teams_complete
    status = st.columns(3)
    status[0].metric(
        "Autosave", "On" if st.session_state.get("autosave", True) else "Off"
    )
    status[1].metric("Pending games", workspace.pending)
    status[2].metric("Corrections", len(workspace.corrections))
    if st.session_state.get("last_saved_at"):
        st.caption(f"Saved at: {st.session_state['last_saved_at']}")
    if st.session_state.get("save_error"):
        st.error(st.session_state["save_error"], icon="💾")
    if st.session_state.get("save_notice"):
        st.success(st.session_state["save_notice"], icon="💾")
    if not can_write:
        st.warning(
            "This legacy report has no complete first-round team data, so it "
            "cannot be saved in the five-sheet format. Rebuild it from the "
            "original bracket files first.",
            icon="📄",
        )

    save_path = st.text_input(
        "Save report as",
        key="save_path",
        persist_state="session",
        help="The editable report path. Names containing 'results' are rejected.",
    )
    actions = st.columns(2)
    with actions[0]:
        if st.button(
            "Save now",
            key="save_now",
            type="primary",
            width="stretch",
            disabled=not can_write,
        ):
            _save_workspace(
                workspace,
                path=Path(save_path),
                label="Saved",
            )
            st.rerun()
    with actions[1]:
        if st.button(
            "Reload saved report",
            key="reload_saved",
            width="stretch",
            disabled=not Path(save_path).exists(),
        ):
            try:
                reloaded = load_report(Path(save_path))
            except ReportError as exc:
                st.error(str(exc))
            else:
                _install_workspace(reloaded, notice="Saved report reloaded.")
                st.rerun()

    st.divider()
    st.subheader("Rebuild from original bracket files")
    st.caption(
        "Rebuilding discards saved actual results, corrections, and entrant edits. "
        "Original bracket files are read-only inputs."
    )
    confirm_rebuild = st.checkbox(
        "I understand the current saved edits will be discarded",
        key="confirm_rebuild",
    )
    if st.button(
        "Rebuild report from raw brackets",
        key="rebuild_report",
        disabled=not confirm_rebuild,
    ):
        folder = Path(st.session_state["data_folder"])
        try:
            rebuilt = build_from_raw(folder, report_path=Path(save_path))
        except (BracketError, ReportError, OSError) as exc:
            st.error(str(exc))
        else:
            _install_workspace(rebuilt)
            if _save_workspace(rebuilt, label="Rebuilt"):
                st.rerun()

    st.divider()
    st.subheader("Download")
    if can_write:
        st.download_button(
            "Download current report (.xlsx)",
            data=_report_bytes(workspace),
            file_name=workspace.report_path.name,
            mime=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
            width="stretch",
        )
    else:
        st.caption("Rebuild the legacy report before downloading a five-sheet copy.")

    st.divider()
    st.subheader("Corrections history")
    if workspace.corrections:
        st.dataframe(
            pd.DataFrame(workspace.corrections),
            hide_index=True,
            width="stretch",
        )
    else:
        st.caption("No entrant corrections have been logged.")


# ---------------------------------------------------------------------------
# Page shell
# ---------------------------------------------------------------------------
st.markdown('<p class="app-kicker">2026 NCAA men’s tournament</p>', unsafe_allow_html=True)
st.markdown(f'<p class="app-title">{escape(APP_NAME)}</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="app-subtitle">Local-folder bracket scoring. The five-sheet '
    "report is the saved state.</p>",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Navigation")
    page = st.radio(
        "Page",
        ["Setup", "Actual Results", "Leaderboard", "Compare", "Save/Load"],
        key="nav",
    )
    st.divider()
    st.toggle(
        "Autosave after result changes",
        key="autosave",
        help="When on, every actual-result change writes the report immediately.",
    )
    workspace_for_status = _workspace()
    if workspace_for_status is not None:
        st.caption(f"Report: {workspace_for_status.report_path.name}")
        if st.session_state.get("last_saved_at"):
            st.caption(f"Saved at: {st.session_state['last_saved_at']}")
        if st.session_state.get("save_error"):
            st.caption("Last save failed; unsaved edits are still in memory.")
        else:
            st.caption("All changes are saved." if st.session_state.get("autosave") else "Autosave is off.")
    st.divider()
    st.caption(f"App {APP_VERSION} · {REPORT_FORMAT_NAME}")

if page == "Setup":
    _render_setup()
elif page == "Actual Results":
    _render_actual_results()
elif page == "Leaderboard":
    _render_leaderboard()
elif page == "Compare":
    _render_compare()
else:
    _render_save_load()
