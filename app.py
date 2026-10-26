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
PAGE_LABELS: dict[str, str] = {
    "Setup": "Setup",
    "Actual Results": "Results",
    "Leaderboard": "Leaderboard",
    "Save/Load": "Save/Load",
}
NAV_OPTIONS = list(PAGE_LABELS)

st.set_page_config(
    page_title=APP_NAME,
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
      :root {
        --app-surface: rgba(128,128,128,.055);
        --app-surface-strong: rgba(128,128,128,.09);
        --app-border: rgba(128,128,128,.18);
        --app-border-strong: rgba(128,128,128,.28);
        --app-radius: .9rem;
      }
      .block-container { padding-top: 1.35rem; padding-bottom: 3rem;
                         padding-left: 2rem; padding-right: 2rem;
                         max-width: 1500px; }

      /* App shell */
      div:has(> [class*="st-key-app_topbar"]) {
        position: sticky !important;
        top: 3.35rem !important;
        z-index: 999;
      }
      [class*="st-key-app_topbar"] {
        position: static !important;
        z-index: 999;
        padding: .7rem .85rem;
        margin-bottom: 1rem;
        border: 1px solid var(--app-border);
        border-radius: var(--app-radius);
        background: var(--background-color, Canvas);
        background: color-mix(in srgb, var(--background-color, Canvas) 90%, transparent);
        backdrop-filter: blur(16px);
        box-shadow: 0 10px 30px rgba(0,0,0,.055);
      }
      .app-brand { display: flex; align-items: center; gap: .65rem; min-width: 0; }
      .app-brand-mark { display: grid; place-items: center; flex: 0 0 auto;
                        width: 2.05rem; height: 2.05rem; border-radius: .62rem;
                        background: color-mix(in srgb, var(--primary-color, #f97316) 14%, transparent);
                        font-size: 1.12rem; }
      .app-brand-copy { min-width: 0; }
      .app-brand-name { display: block; font-size: .96rem; font-weight: 700;
                        letter-spacing: -.015em; line-height: 1.2;
                        white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
      .app-brand-meta { display: block; margin-top: .13rem; font-size: .66rem;
                        letter-spacing: .085em; text-transform: uppercase;
                        opacity: .52; white-space: nowrap; }
      [class*="st-key-nav"] { min-width: 0; }
      [class*="st-key-topbar_status"] button { border-radius: .62rem; font-size: .8rem; }

      /* Page hierarchy */
      .app-page-head { margin: .05rem 0 1rem; }
      .app-page-kicker { margin-bottom: .28rem; font-size: .68rem; font-weight: 700;
                         letter-spacing: .13em; text-transform: uppercase; opacity: .52; }
      .app-page-title { margin: 0; font-size: clamp(1.65rem, 2.8vw, 2.05rem);
                        font-weight: 720; letter-spacing: -.03em; line-height: 1.15; }
      .app-page-subtitle { margin: .32rem 0 0; max-width: 75ch; font-size: .88rem;
                           line-height: 1.5; opacity: .66; }
      .section-head { margin: 1.35rem 0 .55rem; }
      .section-head .section-title { margin: 0; font-size: 1.02rem; font-weight: 680;
                         letter-spacing: -.015em; }
      .section-head p { margin: .2rem 0 0; max-width: 78ch; font-size: .8rem;
                        line-height: 1.45; opacity: .6; }

      /* Cards and compact metadata */
      [class*="st-key-card_"] {
        margin-bottom: .85rem;
        padding: .85rem 1rem .8rem;
        border: 1px solid var(--app-border);
        border-radius: var(--app-radius);
        background: var(--app-surface);
        gap: .55rem !important;
      }
      [class*="st-key-actual_toolbar"] {
        margin: .55rem 0 1rem;
        padding: .55rem .7rem .5rem;
        border: 1px solid var(--app-border);
        border-radius: .72rem;
        background: var(--app-surface);
        gap: .35rem !important;
      }
      .card-head { display: flex; align-items: flex-start; justify-content: space-between;
                   gap: .75rem; margin-bottom: .12rem; }
      .card-title { margin: 0; font-size: 1rem; font-weight: 680;
                    letter-spacing: -.015em; line-height: 1.3; }
      .card-desc { margin: .18rem 0 0; max-width: 76ch; font-size: .8rem;
                   line-height: 1.45; opacity: .62; }
      .app-badge { display: inline-flex; align-items: center; gap: .3rem;
                   flex: 0 0 auto; padding: .16rem .48rem; border-radius: 999px;
                   border: 1px solid var(--app-border-strong); font-size: .68rem;
                   font-weight: 650; letter-spacing: .025em; line-height: 1.35;
                   white-space: nowrap; }
      .app-badge-success { background: rgba(34,197,94,.13);
                           border-color: rgba(34,197,94,.38); }
      .app-badge-warning { background: rgba(245,158,11,.13);
                           border-color: rgba(245,158,11,.4); }
      .app-meta { display: flex; flex-wrap: wrap; align-items: center; gap: .3rem;
                  margin: .05rem 0 .1rem; font-size: .78rem; opacity: .72; }
      .app-meta .sep { opacity: .32; }
      .app-meta strong { font-weight: 650; opacity: 1; }
      .detail-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(8rem, 1fr));
                     gap: .5rem; margin: .15rem 0 .35rem; }
      .detail-item { padding: .5rem .62rem; border-radius: .55rem;
                     background: var(--app-surface-strong); }
      .detail-item .label { display: block; font-size: .64rem; font-weight: 650;
                            letter-spacing: .07em; text-transform: uppercase; opacity: .52; }
      .detail-item .value { display: block; margin-top: .16rem; font-size: .86rem;
                            font-weight: 650; overflow-wrap: anywhere; }

      div[data-testid="stMetric"] { border: 1px solid var(--app-border);
                                    border-radius: .72rem; padding: .55rem .75rem;
                                    background: var(--app-surface); }
      div[data-testid="stMetricLabel"] { font-size: .76rem; opacity: .66; }
      div[data-testid="stMetricValue"] { font-size: 1.28rem; }
      div[data-testid="stExpander"] { border-color: var(--app-border); border-radius: .75rem; }
      footer { visibility: hidden; }
      .entrant-card { display: flex; flex-direction: column; gap: .22rem; }
      .entrant-team-row { display: flex; align-items: center; justify-content: space-between;
                          gap: .3rem; min-height: 1.65rem; padding: 0 .3rem;
                          border-radius: .42rem; border: 1px solid rgba(128,128,128,.24);
                          background: rgba(128,128,128,.055); font-size: .68rem;
                          font-weight: 650; line-height: 1.15; }
      .entrant-team-row.picked.correct { background: rgba(34,197,94,.18);
                                         border-color: rgba(34,197,94,.55); }
      .entrant-team-row.picked.incorrect { background: rgba(239,68,68,.16);
                                           border-color: rgba(239,68,68,.52); }
      .entrant-team-row.picked.pending { background: rgba(128,128,128,.12);
                                         border-color: rgba(128,128,128,.32); opacity: .88; }
      .entrant-team-name { min-width: 0; overflow: hidden; text-overflow: ellipsis;
                           white-space: nowrap; }
      .entrant-mark { flex: 0 0 auto; font-size: .82rem; font-weight: 800; line-height: 1; }
      .entrant-mark.correct { color: #22c55e; }
      .entrant-mark.incorrect { color: #ef4444; }
      .entrant-mark.pending { color: #9aa3b1; }
      .entrant-result { display: flex; align-items: center; flex-wrap: wrap;
                        gap: .22rem; row-gap: .08rem; padding: 0 .12rem;
                        font-size: .54rem; font-weight: 650;
                        letter-spacing: .05em; line-height: 1.2;
                        text-transform: uppercase; opacity: .82; }
      .entrant-result-label { min-width: 0; }
      .entrant-result-note { color: #22c55e; font-weight: 500;
                             letter-spacing: 0; text-transform: none; opacity: .95; }
      .entrant-result-mark { font-weight: 800; }
      .entrant-result-mark.correct { color: #22c55e; }
      .entrant-result-mark.incorrect { color: #ef4444; }
      .entrant-result-mark.pending { color: #9aa3b1; }
      .entrant-card.play-in { gap: .12rem; }
      .entrant-card.play-in .entrant-team-row { min-height: 1.2rem; font-size: .62rem; }
      .entrant-card.play-in .entrant-result { font-size: .48rem; line-height: 1.1; }
      [class*="st-key-entrant_bracket"] [class*="st-key-matchup_"] {
        height: auto !important; min-height: 5.6rem; }
      [class*="st-key-entrant_bracket"] [class*="st-key-matchup_"] > div {
        height: auto !important; min-height: 0 !important;
        max-height: none !important; flex-shrink: 0 !important; }
      [class*="st-key-matchup_"] div[data-testid="stMarkdownContainer"] {
        margin-bottom: 0 !important; }
      .saved-path { font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
                    font-size: .82rem; opacity: .8; overflow-wrap: anywhere; }

      /* Actual-results bracket board */
      :root { --bracket-pitch: 112px; --bracket-gap: 4px; }
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
        :root { --bracket-pitch: 112px; }
        [class*="st-key-matchup_"] button { font-size: .62rem; }
        .bracket-path { display: none; }
      }
      @media (max-width: 900px) {
        /* Stack the three panels, but keep each region's round columns. */
        [class*="st-key-actual_bracket"] > div > div[data-testid="stHorizontalBlock"],
        [class*="st-key-entrant_bracket"] > div > div[data-testid="stHorizontalBlock"] {
          flex-direction: column !important;
          flex-wrap: nowrap !important;
        }
        [class*="st-key-actual_bracket"] > div > div[data-testid="stHorizontalBlock"] > div,
        [class*="st-key-entrant_bracket"] > div > div[data-testid="stHorizontalBlock"] > div {
          width: 100% !important;
          flex: 1 1 100% !important;
        }
        [class*="st-key-entrant_bracket"] [class*="st-key-region_"] > div > div[data-testid="stHorizontalBlock"] {
          flex-direction: column !important;
          flex-wrap: nowrap !important;
        }
        [class*="st-key-entrant_bracket"] [class*="st-key-region_"] > div > div[data-testid="stHorizontalBlock"] > div {
          width: 100% !important;
          flex: 1 1 100% !important;
        }
        [class*="st-key-entrant_bracket"] div[data-testid="stVerticalBlock"][class*="st-key-align_"] {
          height: auto !important;
          min-height: 0 !important;
          max-height: none !important;
        }
        [class*="st-key-entrant_bracket"] [class*="st-key-round_headers_"] {
          display: none !important;
        }
        [class*="st-key-app_topbar"] {
          position: static;
          padding: .6rem .7rem;
        }
        div:has(> [class*="st-key-app_topbar"]) {
          position: static !important;
        }
        .app-brand-meta { display: none; }
        .block-container { padding-left: 1rem; padding-right: 1rem; }
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
    "nav": "Setup",
    "report_path": str(DEFAULT_DATA_FOLDER / "bracket_report.xlsx"),
    "data_folder": str(DEFAULT_DATA_FOLDER),
    "saved_picks": None,
    "undo_stack": [],
    "last_saved_at": None,
    "save_error": None,
    "save_notice": None,
    "autosave": True,
    "leaderboard_entrant": None,
    "confirm_rebuild": False,
    "setup_confirm_context": None,
    "confirm_reload": False,
    "save_path": "",
    "pending_save_path": None,
    "report_path_sync": None,
    "autoload_report": None,
    "correction_slot": "CH",
    "correction_entrant": 0,
    "correction_reason": "",
    "correction_confirmed": False,
}
for _key, _value in _STATE_DEFAULTS.items():
    if _key not in st.session_state:
        st.session_state[_key] = _value


def _workspace() -> ReportSession | None:
    return st.session_state.get("workspace")


def _plural(count: int, singular: str, plural: str | None = None) -> str:
    return singular if count == 1 else (plural or f"{singular}s")


def _page_header(title: str, subtitle: str, *, eyebrow: str | None = None) -> None:
    kicker = (
        f'<div class="app-page-kicker">{escape(eyebrow)}</div>' if eyebrow else ""
    )
    st.markdown(
        f'<div class="app-page-head">{kicker}'
        f'<h1 class="app-page-title">{escape(title)}</h1>'
        f'<p class="app-page-subtitle">{escape(subtitle)}</p></div>',
        unsafe_allow_html=True,
    )


def _section_title(title: str, description: str | None = None) -> None:
    desc = (
        f"<p>{escape(description)}</p>" if description else ""
    )
    st.markdown(
        f'<div class="section-head"><div class="section-title" role="heading" '
        f'aria-level="2">{escape(title)}</div>{desc}</div>',
        unsafe_allow_html=True,
    )


def _card_header(
    title: str,
    description: str | None = None,
    *,
    badge: str | None = None,
    tone: str = "neutral",
) -> None:
    desc = f'<p class="card-desc">{escape(description)}</p>' if description else ""
    chip = (
        f'<span class="app-badge app-badge-{escape(tone)}">{escape(badge)}</span>'
        if badge
        else ""
    )
    st.markdown(
        f'<div class="card-head"><div><div class="card-title" role="heading" '
        f'aria-level="2">{escape(title)}</div>'
        f"{desc}</div>{chip}</div>",
        unsafe_allow_html=True,
    )


def _short_time(value: object) -> str:
    text = str(value or "").strip()
    return text.split(" ")[-1][:5] if text else ""


def _render_topbar_status() -> None:
    workspace = _workspace()
    save_error = st.session_state.get("save_error")
    autosave = bool(st.session_state.get("autosave", True))
    saved_at = st.session_state.get("last_saved_at")
    dirty = bool(
        workspace is not None
        and st.session_state.get("saved_picks") is not None
        and workspace.actual.picks != st.session_state.get("saved_picks")
    )
    if workspace is None:
        label = "No report"
    elif save_error:
        label = "Save failed"
    elif dirty and not autosave:
        label = "Unsaved changes"
    elif saved_at:
        label = f"Saved {_short_time(saved_at)}"
    else:
        label = "Report open"

    with st.popover(
        label,
        key="topbar_status",
        icon=":material/tune:",
        width="stretch",
        help="Workspace status, autosave, and app details.",
    ):
        if workspace is None:
            st.caption("No report is open. Choose a folder on Setup to begin.")
        else:
            st.markdown(
                f'<div class="detail-item"><span class="label">Open report</span>'
                f'<span class="value">{escape(workspace.report_path.name)}</span></div>',
                unsafe_allow_html=True,
            )
            st.caption(str(workspace.report_path))
            if save_error:
                st.error(str(save_error), icon="💾")
            elif saved_at:
                st.caption(f"Last saved {saved_at}")
            else:
                st.caption("Not saved yet.")
            if dirty and not autosave:
                st.warning("Changes are waiting to be saved.", icon="💾")
        st.toggle(
            "Autosave after result changes",
            key="autosave",
            help="When on, every actual-result change writes the report immediately.",
        )
        if not st.session_state.get("autosave", True):
            st.caption("Autosave is off; use Save/Load to write changes.")
        st.caption(f"App {APP_VERSION} · {REPORT_FORMAT_NAME}")


def _render_app_shell() -> str:
    with st.container(key="app_topbar"):
        brand_col, nav_col, status_col = st.columns(
            [2.1, 4.3, 1.6], gap="small", vertical_alignment="center"
        )
        with brand_col:
            st.markdown(
                f'<div class="app-brand"><span class="app-brand-mark">🏀</span>'
                f'<span class="app-brand-copy"><span class="app-brand-name">'
                f'{escape(APP_NAME)}</span><span class="app-brand-meta">'
                "2026 NCAA men’s tournament</span></span></div>",
                unsafe_allow_html=True,
            )
        with nav_col:
            selected = st.segmented_control(
                "Page",
                NAV_OPTIONS,
                format_func=lambda option: PAGE_LABELS[option],
                key="nav",
                label_visibility="collapsed",
                width="stretch",
                wrap=True,
            )
        with status_col:
            _render_topbar_status()

    page = selected or st.session_state.get("nav") or "Setup"
    if page not in NAV_OPTIONS:
        page = "Setup"
        st.session_state["nav"] = page
    return page


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


def _render_validation_status(workspace: ReportSession, *, expanded: bool = False) -> None:
    warnings = _all_warnings(workspace)
    if not warnings:
        st.markdown(
            '<span class="app-badge app-badge-success">Validated · no warnings</span>',
            unsafe_allow_html=True,
        )
        return
    with st.expander(f"Validation warnings ({len(warnings)})", expanded=expanded):
        for message in warnings:
            st.warning(message, icon="⚠️")


def _render_save_feedback() -> None:
    if st.session_state.get("save_error"):
        st.error(st.session_state["save_error"], icon="💾")
        return
    notice = st.session_state.pop("save_notice", None)
    if notice:
        st.success(str(notice), icon="💾")


def _render_setup() -> None:
    _page_header(
        "Setup",
        "Choose a workspace, open a saved report, or build one from the original "
        "bracket files.",
    )

    # Keep the editable Setup path in step with saves, Save As, and reports
    # opened from another page.
    path_sync = st.session_state.get("report_path_sync")
    if path_sync:
        st.session_state["report_path"] = path_sync
        st.session_state["report_path_sync"] = None

    with st.container(key="card_workspace"):
        _card_header(
            "Workspace",
            "Reports are discovered non-recursively and become the saved state.",
        )
        folder_col, rescan_col = st.columns(
            [4.5, 1], gap="small", vertical_alignment="bottom"
        )
        with folder_col:
            folder_text = st.text_input(
                "Folder",
                key="data_folder",
                persist_state="session",
                help=(
                    "A local folder. It is scanned non-recursively for .xlsx, "
                    ".xlsm, and .csv."
                ),
            )
        with rescan_col:
            if st.button("Rescan", key="rescan_folder", width="stretch"):
                # Refresh the scan without discarding the typed report path or
                # the selected actual-results file.
                st.session_state["scan"] = None
                st.rerun()

        scan = _folder_scan(folder_text)
        if scan is None:
            st.error(
                st.session_state.get("scan_error") or "The folder could not be scanned."
            )
            return

        summary = [
            f"<strong>{len(scan.raw_files)}</strong> bracket "
            f"{_plural(len(scan.raw_files), 'file')}",
            f"<strong>{len(scan.reports)}</strong> saved "
            f"{_plural(len(scan.reports), 'report')}",
            f"<strong>{len(scan.actual_candidates)}</strong> results "
            f"{_plural(len(scan.actual_candidates), 'candidate')}",
        ]
        summary_html = '<span class="sep">·</span>'.join(summary)
        st.markdown(
            f'<div class="app-meta">{summary_html}</div>',
            unsafe_allow_html=True,
        )

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
        report_name = st.session_state["saved_report_choice"]
        report_file = next(path for path in scan.reports if path.name == report_name)

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
                _install_workspace(workspace)
                st.rerun()

        saved_workspace = _workspace()
        report_is_open = bool(
            saved_workspace is not None
            and saved_workspace.report_path.resolve() == report_file.resolve()
        )
        warnings = (
            _all_warnings(saved_workspace)
            if report_is_open and saved_workspace is not None
            else []
        )
        if report_is_open and warnings:
            badge, tone = f"{len(warnings)} warnings", "warning"
        elif report_is_open:
            badge, tone = "Open", "success"
        else:
            badge, tone = "Available", "neutral"

        with st.container(key="card_saved_report"):
            _card_header(
                "Saved report",
                "Open the report that holds the current picks, actual results, "
                "and corrections.",
                badge=badge,
                tone=tone,
            )
            report_name = st.selectbox(
                "Report",
                report_names,
                key="saved_report_choice",
            )
            report_file = next(
                path for path in scan.reports if path.name == report_name
            )
            report_is_open = bool(
                saved_workspace is not None
                and saved_workspace.report_path.resolve() == report_file.resolve()
            )
            if report_is_open and saved_workspace is not None:
                st.markdown(
                    f'<div class="app-meta"><strong>{len(saved_workspace.entrants)}'
                    f'</strong> entrants<span class="sep">·</span>'
                    f'<strong>{saved_workspace.pending}</strong> pending'
                    f'<span class="sep">·</span><strong>'
                    f'{len(saved_workspace.corrections)}</strong> corrections</div>',
                    unsafe_allow_html=True,
                )
            st.caption(str(report_file))
            label = "Reload report" if report_is_open else "Open report"
            if st.button(
                label,
                key="open_saved_report",
                type="secondary" if report_is_open else "primary",
                width="stretch",
            ):
                try:
                    workspace = load_report(report_file)
                except ReportError as exc:
                    st.error(str(exc))
                else:
                    _install_workspace(workspace)
                    st.rerun()
            if report_is_open and saved_workspace is not None:
                _render_validation_status(saved_workspace)
            elif saved_workspace is not None:
                st.caption(
                    f"Currently editing `{saved_workspace.report_path}` from "
                    "another folder."
                )
    else:
        with st.container(key="card_saved_report"):
            _card_header(
                "Saved report",
                "This folder has no saved report yet. Use the rebuild section below "
                "to create one.",
                badge="None",
            )
            if saved_workspace is not None:
                st.caption(
                    f"Currently editing `{saved_workspace.report_path}` from another "
                    "folder."
                )

    with st.expander(
        "Create or rebuild from bracket files", expanded=not scan.reports
    ):
        st.caption(
            "Building a report writes the five-sheet workbook and makes it the "
            "saved state. Rebuilding discards saved edits and corrections."
        )
        if not scan.raw_files:
            st.warning(
                "This folder has no raw bracket files, so a report cannot be "
                "rebuilt here. Continue the saved report instead.",
                icon="📄",
            )
        else:
            confirm_context = (
                str(scan.folder),
                tuple(path.name for path in scan.reports),
            )
            if st.session_state.get("setup_confirm_context") != confirm_context:
                st.session_state["setup_confirm_rebuild"] = not scan.reports
                st.session_state["setup_confirm_context"] = confirm_context
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
            actual_file = next(
                path for path in scan.raw_files if path.name == actual_name
            )
            st.caption(
                f"Entrants will be built from the other {len(scan.raw_files) - 1} "
                f"raw file(s). Actual: `{actual_file.name}`"
            )
            confirm = st.checkbox(
                "Replace any saved edits in the report at this path",
                key="setup_confirm_rebuild",
            )
            report_text = str(st.session_state.get("report_path", "")).strip()
            report_target = Path(report_text) if report_text else None
            st.caption(
                f"Report destination: `{report_target}`"
                if report_target is not None
                else "Set a report path in Advanced before creating a report."
            )
            if st.button(
                "Rebuild from original bracket files"
                if scan.reports
                else "Create report from brackets",
                key="create_report",
                type="primary",
                disabled=not confirm or report_target is None,
            ):
                try:
                    workspace = build_from_raw(
                        scan.folder,
                        actual_path=actual_file,
                        report_path=report_target,
                    )
                except (BracketError, ReportError, OSError) as exc:
                    st.error(str(exc))
                else:
                    _install_workspace(workspace)
                    _save_workspace(workspace, label="Report created")
                    st.rerun()

    with st.expander("Advanced: paths and report details", expanded=False):
        st.text_input(
            "Report path",
            key="report_path",
            persist_state="session",
            help="The saved report. Names containing 'results' are rejected.",
        )
        st.caption(
            "Report filenames may not contain 'results'. Raw bracket files are "
            "never overwritten."
        )
        workspace = _workspace()
        if workspace is None:
            st.caption("No report is open. The report path is used when creating one.")
        else:
            details = [
                ("Schema", workspace.state.get("Report schema version", "—")),
                ("Rules", workspace.state.get("Scoring rules version", "—")),
                ("App", workspace.state.get("App version", APP_VERSION)),
                (
                    "Source folder",
                    Path(
                        workspace.source_folder or workspace.report_path.parent
                    ).name,
                ),
            ]
            items = "".join(
                f'<div class="detail-item"><span class="label">{escape(label)}</span>'
                f'<span class="value">{escape(str(value))}</span></div>'
                for label, value in details
            )
            st.markdown(f'<div class="detail-grid">{items}</div>', unsafe_allow_html=True)
            _render_validation_status(workspace, expanded=False)


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
    result_map=None,
    entrant=None,
) -> None:
    slot = SLOTS_BY_ID[slot_id]
    current = workspace.actual.picks.get(slot_id, "").strip()
    options = _matchup_options(slot_id, workspace)
    card_label = label or f"Game {slot.game}"
    if result_map is not None and label is None:
        card_label = f"{slot.round} · Game {slot.game}"
    if len(options) > 2:
        card_label += " · Play-in"

    with st.container(key=f"matchup_{slot_id}"):
        st.markdown(
            f'<div class="bracket-game-label">{escape(card_label)}</div>',
            unsafe_allow_html=True,
        )
        if result_map is not None:
            result = result_map[slot_id]
            pick = (result.pick or "").strip()
            teams: list[str] = []
            if entrant is not None:
                for team in available_picks(
                    slot_id, workspace.team_pairs, entrant.picks
                ):
                    if team and not any(
                        team_matches(team, existing) for existing in teams
                    ):
                        teams.append(team)
            if pick and not any(team_matches(pick, existing) for existing in teams):
                teams.append(pick)
            rows: list[str] = []
            for team in teams:
                picked = bool(pick and team_matches(pick, team))
                row_class = (
                    f"entrant-team-row picked {result.status}"
                    if picked
                    else "entrant-team-row"
                )
                mark = ""
                if picked:
                    symbol = (
                        "✓"
                        if result.status == "correct"
                        else "✗"
                        if result.status == "incorrect"
                        else "–"
                    )
                    mark = (
                        f'<span class="entrant-mark {result.status}">'
                        f"{symbol}</span>"
                    )
                rows.append(
                    f'<div class="{row_class}">'
                    f'<span class="entrant-team-name">'
                    f"{escape(_seed_label(team, seed_map))}</span>"
                    f"{mark}</div>"
                )
            points_label = (
                f"{result.points} pt"
                if result.points == 1
                else f"{result.points} pts"
            )
            result_label = f"{result.status.title()} - {points_label}"
            correct_note = ""
            if result.status == "incorrect" and result.actual:
                correct_note = (
                    f'<span class="entrant-result-note">'
                    f"({escape(result.actual)})</span>"
                )
            symbol = (
                "✓"
                if result.status == "correct"
                else "✗"
                if result.status == "incorrect"
                else "–"
            )
            tooltip = (
                f"{slot_id} | Actual: {result.actual or 'Pending'} | "
                f"Pick: {result.pick or 'Blank'} | {result.status.title()} | "
                f"{result.points} pts"
            )
            card_class = (
                "entrant-card play-in" if len(teams) > 2 else "entrant-card"
            )
            st.markdown(
                f'<div class="{card_class}" title="{escape(tooltip)}">'
                f'{"".join(rows)}'
                f'<div class="entrant-result {result.status}">'
                f'<span class="entrant-result-mark {result.status}">'
                f"{symbol}</span>"
                f'<span class="entrant-result-label">'
                f"{escape(result_label)}</span>"
                f"{correct_note}</div></div>",
                unsafe_allow_html=True,
            )
            return
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
    result_map=None,
    entrant=None,
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
                            _matchup_card(
                                slot_id,
                                workspace,
                                seed_map,
                                result_map=result_map,
                                entrant=entrant,
                            )


def _render_final_board(
    workspace: ReportSession, seed_map: dict[str, int], result_map=None, entrant=None
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
            result_map=result_map,
            entrant=entrant,
        )
        _matchup_card(
            "F4-2",
            workspace,
            seed_map,
            label="F4 Game 2 · West / Midwest",
            result_map=result_map,
            entrant=entrant,
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
            result_map=result_map,
            entrant=entrant,
        )


def _render_entrant_bracket(workspace: ReportSession, entrant) -> None:
    result_map = {
        result.slot_id: result
        for result in score_games(workspace.actual, entrant)
    }
    seed_map = workspace.team_seed_map
    with st.container(key="entrant_bracket"):
        left, center, right = st.columns(
            [5, 2.2, 5], gap="small", vertical_alignment="top", wrap=False
        )
        with left:
            _render_region_board(
                "E", workspace, seed_map, result_map=result_map, entrant=entrant
            )
            _render_region_board(
                "S", workspace, seed_map, result_map=result_map, entrant=entrant
            )
        with center:
            _render_final_board(
                workspace, seed_map, result_map=result_map, entrant=entrant
            )
        with right:
            _render_region_board(
                "W",
                workspace,
                seed_map,
                mirrored=True,
                result_map=result_map,
                entrant=entrant,
            )
            _render_region_board(
                "M",
                workspace,
                seed_map,
                mirrored=True,
                result_map=result_map,
                entrant=entrant,
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
    _page_header(
        "Actual Results",
        "Click a team to set the actual winner. The winner is highlighted; click "
        "it again to return the game to pending. Pending games award no points.",
    )
    workspace = _workspace()
    if workspace is None:
        st.info("Load or create a report on the Setup page first.", icon="🏀")
        return

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
    cards = st.columns(3)
    cards[0].metric("Actual source", workspace.actual.source_name)
    cards[1].metric("Decided games", f"{filled} / {len(SLOT_IDS)}")
    cards[2].metric("Pending games", workspace.pending)
    _render_save_feedback()

    with st.container(key="actual_toolbar"):
        actions = st.columns([1, 1, 2], vertical_alignment="center")
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
    _page_header(
        "Leaderboard",
        "Ranked standings, round-by-round points, and the championship tie-break.",
    )
    workspace = _workspace()
    if workspace is None:
        st.info("Load or create a report on the Setup page first.", icon="🏀")
        return

    scores = workspace.scores
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
    _section_title("Standings", "Select a row to view that entrant's bracket.")
    event = st.dataframe(
        display,
        hide_index=True,
        width="stretch",
        key="leaderboard_table",
        on_select="rerun",
        selection_mode="single-row",
    )
    if event.selection.rows:
        st.session_state["leaderboard_entrant"] = event.selection.rows[0]
    selected_entrant = st.session_state.get("leaderboard_entrant")
    if selected_entrant is not None and not (0 <= selected_entrant < len(scores)):
        selected_entrant = None
        st.session_state["leaderboard_entrant"] = None

    if selected_entrant is None:
        st.caption("Select a row in the standings to view that entrant's bracket.")
    else:
        score = scores[selected_entrant]
        with st.container(key="card_entrant_bracket"):
            _card_header(
                f"{score.entrant}'s bracket",
                "Green = correct · Red = incorrect · Gray = pending actual result.",
                badge=f"Rank #{score.rank}",
                tone="success" if score.rank == 1 else "neutral",
            )
            details = st.columns(4)
            details[0].metric("Total", f"{score.total} / 148")
            details[1].metric("Rank", f"#{score.rank}")
            details[2].metric("Correct picks", f"{score.correct} / {score.decided}")
            details[3].metric("Accuracy", f"{score.accuracy:.1%}")
            _render_entrant_bracket(workspace, score.bracket)

    chart = pd.DataFrame(
        {
            "Entrant": [score.entrant for score in scores],
            "Total": [score.total for score in scores],
        }
    ).set_index("Entrant")
    _section_title("Points by entrant")
    st.bar_chart(chart, height=340, horizontal=True, sort=False)

    st.caption(TIE_BREAK_DESCRIPTION)
    st.download_button(
        "Download standings CSV",
        data=frame.to_csv(index=False).encode("utf-8"),
        file_name="standings.csv",
        mime="text/csv",
        width="stretch",
    )


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
    _page_header(
        "Save / Load",
        "Write the five-sheet report, reload it from disk, export a copy, or "
        "review logged corrections.",
    )
    workspace = _workspace()
    if workspace is None:
        st.info("Load or create a report on the Setup page first.", icon="🏀")
        return

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
    _render_save_feedback()
    if not can_write:
        st.warning(
            "This legacy report has no complete first-round team data, so it "
            "cannot be saved in the five-sheet format. Rebuild it from the "
            "original bracket files first.",
            icon="📄",
        )

    with st.container(key="card_save_report"):
        _card_header(
            "Save report",
            "The current report path is overwritten atomically. Choose another "
            "path to keep a copy.",
            badge="Ready" if can_write else "Read-only",
            tone="success" if can_write else "warning",
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
            reload_target = Path(save_path) if save_path.strip() else None
            if st.button(
                "Reload saved report",
                key="reload_saved",
                width="stretch",
                disabled=reload_target is None or not reload_target.exists(),
            ):
                try:
                    reloaded = load_report(reload_target)
                except ReportError as exc:
                    st.error(str(exc))
                else:
                    _install_workspace(reloaded, notice="Saved report reloaded.")
                    st.rerun()

    with st.expander("Rebuild from original bracket files", expanded=False):
        st.caption(
            "Rebuilding discards saved actual results, corrections, and entrant "
            "edits. Original bracket files are read-only inputs."
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

    with st.container(key="card_download"):
        _card_header(
            "Download",
            "Export the current in-memory report as a five-sheet workbook.",
        )
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

    with st.expander("Correct an entrant pick", expanded=False):
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
        elif not workspace.scores:
            st.caption("This report has no entrants to correct.")
        else:
            if st.session_state.get("correction_entrant", 0) >= len(workspace.scores):
                st.session_state["correction_entrant"] = 0
            selected_correction_index = st.selectbox(
                "Entrant",
                list(range(len(workspace.scores))),
                key="correction_entrant",
                format_func=lambda index: (
                    f"{workspace.scores[index].entrant} — "
                    f"{workspace.scores[index].source_name}"
                ),
            )
            entrant = workspace.scores[selected_correction_index].bracket
            correction_slot = st.selectbox(
                "Game to correct",
                SLOT_IDS,
                key="correction_slot",
                format_func=lambda slot_id: (
                    f"{slot_id} — {SLOT_STANDINGS_LABEL[slot_id]}"
                ),
            )
            current_pick = entrant.picks.get(correction_slot, "").strip()
            options: list[str] = [""]
            for team in available_picks(
                correction_slot, workspace.team_pairs, entrant.picks
            ):
                if team and not any(
                    team_matches(team, existing) for existing in options
                ):
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
                        selected_correction_index,
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

    with st.expander("Corrections history", expanded=False):
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
page = _render_app_shell()

if page == "Setup":
    _render_setup()
elif page == "Actual Results":
    _render_actual_results()
elif page == "Leaderboard":
    _render_leaderboard()
else:
    _render_save_load()
