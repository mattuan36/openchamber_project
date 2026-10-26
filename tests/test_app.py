"""Streamlit AppTest smoke test for the bracket scorekeeper workflow."""

from __future__ import annotations

import shutil
from pathlib import Path

from streamlit.testing.v1 import AppTest

from bracket.store import build_from_raw

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _copy_demo(destination: Path) -> None:
    for path in (PROJECT_ROOT / "sample_data" / "demo").iterdir():
        if path.is_file() and path.suffix.lower() == ".csv":
            shutil.copy2(path, destination / path.name)


def test_streamlit_demo_load_edit_views_save_and_reload(tmp_path: Path) -> None:
    _copy_demo(tmp_path)
    app = AppTest.from_file(str(PROJECT_ROOT / "app.py"), default_timeout=45)
    app.run()
    assert not app.exception

    app.text_input(key="data_folder").set_value(str(tmp_path))
    app.run()
    assert not app.exception
    assert app.session_state.get("scan_error") is None

    app.button(key="create_report").click()
    app.run()
    assert not app.exception
    workspace = app.session_state.get("workspace")
    assert workspace is not None
    assert (tmp_path / "bracket_report.xlsx").exists()
    assert [(score.entrant, score.total) for score in workspace.scores] == [
        ("MATT", 148),
        ("CHRIS", 136),
    ]

    app.segmented_control(key="nav").set_value("Actual Results")
    app.run()
    assert not app.exception
    assert "16 · Siena" in app.button(key="pick_R64-E1_1").label
    board_markup = "\n".join(block.value for block in app.markdown)
    assert "R64 → R32 → S16 → E8" in board_markup
    assert "E8 ← S16 ← R32 ← R64" in board_markup
    assert "Final Four" in board_markup
    assert "Championship" in board_markup

    app.button(key="pick_R64-E1_1").click()
    app.run()
    assert not app.exception
    workspace = app.session_state.get("workspace")
    assert workspace.actual.picks["R64-E1"] == "Siena"
    assert workspace.actual.picks["R32-E1"] == ""
    assert workspace.actual.picks["S16-E1"] == ""
    assert workspace.actual.picks["E8-E1"] == ""
    assert workspace.pending == 3

    # Clicking the highlighted winner again clears the game to pending.
    app.button(key="pick_R64-E1_1").click()
    app.run()
    assert not app.exception
    workspace = app.session_state.get("workspace")
    assert workspace.actual.picks["R64-E1"] == ""
    assert workspace.pending == 4

    app.button(key="pick_R64-E1_1").click()
    app.run()
    assert not app.exception
    workspace = app.session_state.get("workspace")
    assert workspace.actual.picks["R64-E1"] == "Siena"
    assert workspace.pending == 3

    app.segmented_control(key="nav").set_value("Leaderboard")
    app.run()
    assert not app.exception
    metrics = {metric.label: metric.value for metric in app.metric}
    assert metrics["Leader"] == "MATT"
    assert metrics["Pending games"] == "3"

    app.session_state["leaderboard_entrant"] = 1
    app.run()
    assert not app.exception
    bracket_markup = "\n".join(block.value for block in app.markdown)
    assert "CHRIS" in bracket_markup
    assert "entrant-team-row" in bracket_markup
    assert '"entrant-team-row picked correct"' in bracket_markup
    assert '"entrant-team-row picked incorrect"' in bracket_markup
    assert '"entrant-team-row picked pending"' in bracket_markup
    assert "Duke" in bracket_markup
    assert "Siena" in bracket_markup
    assert "Correct - 1 pt" in bracket_markup
    assert "Incorrect - 0 pts" in bracket_markup
    assert "Pending - 0 pts" in bracket_markup

    app.segmented_control(key="nav").set_value("Save/Load")
    app.run()
    assert not app.exception
    assert app.selectbox(key="correction_entrant").value == 0
    assert app.selectbox(key="correction_slot").value == "CH"
    app.button(key="save_now").click()
    app.run()
    assert not app.exception
    assert app.session_state.get("save_error") is None

    app.button(key="reload_saved").click()
    app.run()
    assert not app.exception
    reloaded = app.session_state.get("workspace")
    assert reloaded is not None
    assert reloaded.actual.picks["R64-E1"] == "Siena"
    assert reloaded.actual.picks["R32-E1"] == ""
    assert reloaded.pending == 3
    assert [(score.entrant, score.total) for score in reloaded.scores] == [
        ("MATT", 135),
        ("CHRIS", 123),
    ]

    # Save As moves the active report and the Setup path follows it.
    saved_copy = tmp_path / "saved_copy.xlsx"
    app.text_input(key="save_path").set_value(str(saved_copy))
    app.run()
    app.button(key="save_now").click()
    app.run()
    assert not app.exception
    assert saved_copy.exists()
    app.segmented_control(key="nav").set_value("Setup")
    app.run()
    assert not app.exception
    assert Path(app.text_input(key="data_folder").value) == tmp_path
    assert Path(app.text_input(key="report_path").value) == saved_copy

    # Rescanning refreshes files without discarding the editable path.
    custom_path = tmp_path / "custom_report.xlsx"
    app.text_input(key="report_path").set_value(str(custom_path))
    app.run()
    app.button(key="rescan_folder").click()
    app.run()
    assert not app.exception
    assert Path(app.text_input(key="report_path").value) == custom_path


def test_streamlit_auto_continues_existing_report(tmp_path: Path) -> None:
    _copy_demo(tmp_path)
    build_from_raw(tmp_path).save()

    app = AppTest.from_file(str(PROJECT_ROOT / "app.py"), default_timeout=45)
    app.session_state["data_folder"] = str(tmp_path)
    app.run()
    assert not app.exception

    workspace = app.session_state.get("workspace")
    assert workspace is not None
    assert workspace.report_path == (tmp_path / "bracket_report.xlsx").resolve()
    assert [(score.entrant, score.total) for score in workspace.scores] == [
        ("MATT", 148),
        ("CHRIS", 136),
    ]
