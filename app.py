"""Streamlit starter app.

A small, self-contained workspace demonstrating a secure environment setup,
a sidebar-driven control panel, a responsive column grid, and session-state
caching so computed results survive widget reruns.
"""

from __future__ import annotations

import os
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
# Load `.env` once, without overriding variables that already exist in the
# process environment (container/CI values win). Secrets stay server-side:
# they are never rendered, logged, or sent to the browser.
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=False)

APP_NAME = os.getenv("APP_NAME", "Streamlit Starter")
APP_ENV = os.getenv("APP_ENV", "development")
API_KEY = os.getenv("API_KEY", "")

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
    "has", "have", "in", "is", "it", "its", "of", "on", "or", "that", "the",
    "to", "was", "were", "will", "with", "this", "these", "those", "we", "you",
}


# ---------------------------------------------------------------------------
# Processing logic (pure functions, no Streamlit calls)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Settings:
    """Everything that affects processing output."""

    text: str
    top_n: int
    min_word_length: int
    case_sensitive: bool
    strip_stopwords: bool


@dataclass(frozen=True)
class Results:
    """Immutable snapshot of one processing run."""

    words: int
    characters: int
    sentences: int
    unique_words: int
    reading_minutes: float
    top_terms: pd.DataFrame
    computed_at: datetime


def tokenize(settings: Settings) -> list[str]:
    flags = 0 if settings.case_sensitive else re.IGNORECASE
    tokens = re.findall(r"[^\W_]+(?:['-][^\W_]+)*", settings.text, flags=flags)
    words = [t for t in tokens if len(t) >= settings.min_word_length]
    if settings.strip_stopwords:
        words = [w for w in words if w.lower() not in STOPWORDS]
    return words


def process(settings: Settings) -> Results:
    """Compute the workspace report for the given settings."""
    words = tokenize(settings)
    sentences = len([s for s in re.split(r"[.!?]+", settings.text) if s.strip()])
    counts = Counter(w.lower() if not settings.case_sensitive else w for w in words)

    top_terms = pd.DataFrame(
        [
            {"Term": term, "Count": count, "Share": count / max(len(words), 1)}
            for term, count in counts.most_common(settings.top_n)
        ],
        columns=["Term", "Count", "Share"],
    )

    return Results(
        words=len(words),
        characters=len(settings.text),
        sentences=sentences,
        unique_words=len(counts),
        reading_minutes=round(len(words) / 200, 1),
        top_terms=top_terms,
        computed_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Session-state cache
# ---------------------------------------------------------------------------
# Widget values already persist across reruns; this block keeps the *results*
# of processing too, so changing an unrelated widget (or adding a new one)
# does not wipe the workspace or force a recompute.
STATE_DEFAULTS: dict[str, object] = {
    "results": None,
    "results_key": None,
    "runs": 0,
    "history": [],
}
for state_key, default_value in STATE_DEFAULTS.items():
    if state_key not in st.session_state:
        st.session_state[state_key] = default_value


def settings_key(settings: Settings) -> tuple:
    """Hashable identity of a settings object."""
    return (
        settings.text,
        settings.top_n,
        settings.min_word_length,
        settings.case_sensitive,
        settings.strip_stopwords,
    )


def get_results(settings: Settings, *, force: bool = False) -> Results | None:
    """Return cached results, recomputing only when inputs changed."""
    if not settings.text.strip():
        st.session_state["results"] = None
        st.session_state["results_key"] = None
        return None

    key = settings_key(settings)
    cached = st.session_state["results"]

    if force or cached is None or st.session_state["results_key"] != key:
        cached = process(settings)
        st.session_state["results"] = cached
        st.session_state["results_key"] = key
        st.session_state["runs"] += 1
        st.session_state["history"].insert(
            0,
            {
                "Run": st.session_state["runs"],
                "Words": cached.words,
                "Unique": cached.unique_words,
                "At (UTC)": cached.computed_at.strftime("%H:%M:%S"),
            },
        )
        del st.session_state["history"][8:]

    return cached


# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title=APP_NAME,
    page_icon="🧩",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .block-container { padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1200px; }
      .app-kicker { letter-spacing: .14em; text-transform: uppercase;
                    font-size: .72rem; color: var(--text-color); opacity: .6; }
      .app-title { font-size: 2.1rem; font-weight: 700; letter-spacing: -.02em;
                   margin: .15rem 0 .35rem; }
      .app-subtitle { opacity: .7; margin-bottom: 1.4rem; }
      div[data-testid="stMetric"] { border: 1px solid rgba(128,128,128,.22);
                                    border-radius: .75rem; padding: .85rem 1rem; }
      div[data-testid="stMetricValue"] { font-size: 1.55rem; }
      footer { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<p class="app-kicker">Workspace</p>', unsafe_allow_html=True)
st.markdown(f'<p class="app-title">{escape(APP_NAME)}</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="app-subtitle">Paste text, tune the controls in the sidebar, '
    "and the report refreshes in place.</p>",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Sidebar: inputs
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Controls")
    st.caption("Every control below feeds the processing cache.")

    text = st.text_area(
        "Source text",
        value=(
            "Streamlit turns Python scripts into shareable data apps. "
            "Keep the input controls in the sidebar and the output in a clear, "
            "column-based workspace."
        ),
        height=180,
        placeholder="Paste your text here…",
    )

    with st.expander("Processing options", expanded=True):
        top_n = st.slider("Top terms", 3, 20, 10)
        min_word_length = st.slider("Minimum word length", 1, 10, 3)
        case_sensitive = st.toggle("Case sensitive", value=False)
        strip_stopwords = st.toggle("Ignore stopwords", value=True)

    st.divider()
    force_run = st.button("Re-process now", type="primary", width="stretch")
    if st.session_state["runs"]:
        st.caption(f"Runs this session: {st.session_state['runs']}")

    with st.expander("Environment"):
        st.write(f"**App:** {APP_NAME}")
        st.write(f"**Env:** `{APP_ENV}`")
        st.write("**API key:** " + ("configured" if API_KEY else "not set"))
        st.caption(
            "Values load from `.env` (gitignored) or the process environment. "
            "Secrets are never displayed."
        )

settings = Settings(
    text=text,
    top_n=top_n,
    min_word_length=min_word_length,
    case_sensitive=case_sensitive,
    strip_stopwords=strip_stopwords,
)

results = get_results(settings, force=force_run)

# ---------------------------------------------------------------------------
# Workspace grid
# ---------------------------------------------------------------------------
if results is None:
    st.info("Add some text in the sidebar to build the workspace.", icon="✍️")
    st.stop()

metric_cols = st.columns(4, gap="medium")
metric_cols[0].metric("Words", f"{results.words:,}")
metric_cols[1].metric("Unique words", f"{results.unique_words:,}")
metric_cols[2].metric("Sentences", f"{results.sentences:,}")
metric_cols[3].metric("Reading time", f"{results.reading_minutes} min")

st.write("")

left, right = st.columns([1.7, 1], gap="large")

with left:
    with st.container(border=True):
        st.subheader("Top terms")
        if results.top_terms.empty:
            st.caption("No terms match the current filters.")
        else:
            st.bar_chart(
                results.top_terms.set_index("Term")["Count"],
                horizontal=True,
            )

    with st.container(border=True):
        st.subheader("Term breakdown")
        table = results.top_terms.copy()
        table["Share"] = table["Share"].map(lambda share: f"{share:.1%}")
        st.dataframe(table, hide_index=True, width="stretch")

with right:
    with st.container(border=True):
        st.subheader("Summary")
        st.write(
            f"The current selection covers **{results.words:,} words** across "
            f"**{results.sentences:,} sentences**."
        )
        st.progress(
            min(results.unique_words / results.words, 1.0) if results.words else 0.0,
            text=f"{results.unique_words / max(results.words, 1):.0%} vocabulary variety",
        )
        st.caption(
            f"Last processed at {results.computed_at.astimezone().strftime('%H:%M:%S')} "
            f"· {results.characters:,} characters"
        )

    with st.container(border=True):
        st.subheader("Run history")
        if st.session_state["history"]:
            st.dataframe(
                pd.DataFrame(st.session_state["history"]),
                hide_index=True,
                width="stretch",
            )
        else:
            st.caption("Runs appear here as settings change.")

    st.download_button(
        "Download top terms (CSV)",
        data=results.top_terms.to_csv(index=False).encode("utf-8"),
        file_name="top-terms.csv",
        mime="text/csv",
        width="stretch",
    )
