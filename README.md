# 2026 March Madness Bracket Scorekeeper

A local-folder bracket scorekeeper for the 2026 printable NCAA men's bracket.
It reads filled bracket workbooks, scores every entrant against an
actual-results bracket, and persists everything in a five-sheet Excel report.
The same reusable core is used by the Streamlit UI and the command line.

## Quick start

Python 3.11 or newer is required. Tested with Python 3.14.3 and
Streamlit 1.66.1.

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Streamlit app (opens with sample_data\demo as the default folder)
streamlit run app.py

# CLI: score the bundled demo and write bracket_report.xlsx
python scorekeeper.py --input sample_data\demo

# Validate without writing a report
python scorekeeper.py --input sample_data\demo --validate-only
```

The bundled sample data contains:

| File | Role |
| --- | --- |
| `sample_data/demo/2026_results.csv` | Actual results (`NAME: OFFICIAL`) |
| `sample_data/demo/2026_bracket_MATT.csv` | Perfect entrant, 148 points |
| `sample_data/demo/2026_bracket_CHRIS.csv` | Championship pick Houston, 136 points |
| `sample_data/2026_basketball_bracket_MAT.csv` | Full template fixture, also 148 against itself |

## Streamlit workflow

Run `streamlit run app.py`. The top bar navigates between **Setup**,
**Results**, **Leaderboard**, and **Save/Load**, and shows the open
report, last save, and autosave settings. Setup defaults to `sample_data/demo`;
any local folder path can be entered.

1. **Setup** scans the folder non-recursively for `.xlsx`, `.xlsm`, and `.csv`.
   Excel owner files (`~$...`) and generated reports are ignored as raw
   brackets. The actual-results file is auto-selected by `results` in its
   filename, with a manual override inside the collapsed rebuild section.
2. If the folder already contains a saved report, a fresh session opens it
   automatically. The saved-report card keeps the current report, entrant,
   pending, and correction counts together; **Create or rebuild from bracket
   files** is collapsed and explicitly discards saved edits and corrections.
3. If no report exists, the create section opens automatically and **Create
   report from brackets** builds the initial report at the configured path.
   The folder, report path, schema, and rules details live in **Advanced**.
4. **Actual Results** is a three-panel bracket board for editing actual winners
   only: East and South read inward from the left, West and Midwest are mirrored
   inward from the right, and the Final Four and Championship sit in the center.
   Every matchup shows both teams with their seeds and a light border; later
   rounds are vertically aligned with their feeder games. Click a team to choose
   it (the winner is highlighted) and click the highlighted winner again to
   return the game to pending. Changing a feeder winner clears downstream picks
   that are no longer possible. Standings and scores recalculate immediately.
5. **Leaderboard** shows metric cards, a ranked table with round points,
   correct picks, pending games, accuracy, and a total-points bar chart. Select
   a row in the standings to open that entrant's bracket. Every matchup shows
   both teams and a result line: correct picks are green with a check, incorrect
   picks red with an X, and pending picks gray with a dash. The page also shows
   the tie-break rule and a CSV download.
6. **Save/Load** saves now, reloads the saved report, rebuilds from raw
   brackets, downloads the current report, and records entrant corrections and
   their history.

### Local folder and persistence

- The saved report is `<data folder>/bracket_report.xlsx` by default. The
  report path is editable.
- Report filenames containing `results` are rejected so they cannot be mistaken
  for the actual-results input.
- Raw bracket inputs are never modified or overwritten. Overwriting a saved
  report is allowed.
- Writes are atomic through a temporary file in the destination folder.
- If Excel has locked the report, the app shows a clear message and keeps the
  unsaved state in memory. Close the workbook in Excel and save again.
- Autosave after each actual-result change is on by default and is controlled
  from the top-bar report status popover. The same popover shows the open
  report, last save, and any save error.
- After creation, the report is the source of truth. Original bracket files are
  used only for bootstrap or an explicit rebuild.
- Older two-sheet reports still open for viewing and scoring, but they contain no
  first-round team data. They are read-only until rebuilt from the original
  bracket files, so a save cannot produce an incomplete five-sheet report.
- Older five-sheet reports with the four-column Teams layout keep loading
  names-only. Their seeds are blank until the report is rebuilt from the
  original bracket files; the Actual Results page shows a rebuild hint.

### Entrant correction policy

Entrant picks are read-only during normal use. Save/Load contains an advanced
**Correct an entrant pick** control. It requires a reason and an explicit
confirmation, validates the corrected team against the bracket, appends an
entry to the **Corrections** sheet, and saves it with the report. Existing
correction entries are loaded and never discarded on save.

## Five-sheet report contract

Every report has exactly these visible sheets, in this order. There is no
hidden state sheet.

### Picks

`Picks` is the single source of truth for participants and picks.

- Row 1 is the header. Columns A and B are `Source File` and `Entrant`.
  Columns C through BM are the 63 games in canonical `SLOT_IDS` order.
- Row 2 is the actual results. Its Entrant label is `ACTUAL — <name>` and its
  Source File comes from column A.
- Rows 3 and below are entrants.
- Columns are loaded by header name, not fixed position, so reordered columns
  still load correctly.
- Entrant names, source filenames, and picks are **not** duplicated in State.

### Standings

Derived on load and recalculated during edits. Stored ranks and scores are
never trusted. The sheet shows rank, entrant, source file, points per round,
total, correct picks, pending games, and accuracy.

### State

Visible key/value metadata only:

| Key | Meaning |
| --- | --- |
| Report schema version | Current report contract version (`3`) |
| Created (UTC) | Original creation timestamp |
| Updated (UTC) | Last save timestamp |
| Source folder | Folder the report was built from |
| Scoring rules version | Rules/scoring revision |
| App version | Scorekeeper version |
| Report format | Human-readable format name |

State contains no entrant names, picks, or source filenames.

### Teams

Exactly the 32 first-round matchups. New reports use `Slot`, `Region`, `Seed 1`,
`Team 1`, `Seed 2`, and `Team 2`; the seeds are the printed tournament seeds.
Play-in rows keep both entrants in one cell (for example,
`Texas / NC State`) with the shared printed seed repeated for each team in the
board. Older four-column reports still load names-only. The sheet is derived
from the actual bracket. If an entrant bracket prints a different first-round
matchup, loading emits a warning and the actual bracket remains authoritative.
These matchups and seeds supply valid team options while editing.

### Corrections

An append-only audit log with `Timestamp`, `Entrant`, `Source File`, `Slot`,
`Old Pick`, `New Pick`, and `Reason`. Existing entries are loaded and
preserved by saves.

## Scoring

| Round | Games | Points per correct pick | Maximum |
| --- | ---: | ---: | ---: |
| Round of 64 | 32 | 1 | 32 |
| Round of 32 | 16 | 2 | 32 |
| Sweet 16 | 8 | 4 | 32 |
| Elite Eight | 4 | 6 | 24 |
| Final Four | 2 | 8 | 16 |
| Championship | 1 | 12 | 12 |
| **Total** | **63** | | **148** |

A blank actual-results cell means the game is **pending**. It awards no points,
is excluded from the accuracy denominator, and is never counted as incorrect.
A blank entrant pick is worth zero once the game is decided and counts as a
miss. Accuracy is `correct picks / decided games`, not `correct picks / 63`.

Ties are broken by total points, then championship, Final Four, Elite Eight,
Sweet 16, Round of 32, and Round of 64 correct picks, then entrant name. Tied
entrants share a competition rank (`1, 2, 2, 4`).

## Input rules

- Accepts `.xlsx`, `.xlsm`, or `.csv` (CSV is a preview format).
- A folder is scanned non-recursively. A single workbook can also be passed to
  the CLI.
- The actual-results workbook is the one whose filename contains `results`
  (case-insensitive). Use `--actual PATH` or the Setup override when the
  filename does not contain it or when more than one candidate exists.
- Every raw workbook must be the 2026 printable bracket template. The loader
  finds the `NAME:` cell, the EAST/WEST/SOUTH/MIDWEST labels, the round headers,
  and `2026 NCAA CHAMPION`, then maps all 63 games from that geometry.
- Parsed first-round team pairs and printed seeds are attached to each bracket
  and used for the Teams sheet, the bracket board, and valid-pick editing.
- The actual-results file is validated strictly. Malformed entrant files stop
  the CLI unless `--skip-invalid` is used; the app skips them with warnings.
- The upper printable bracket is authoritative. The lower duplicate picks
  block is not read.

## CLI

```text
python scorekeeper.py [-i PATH] [--actual PATH] [-o PATH]
                      [--skip-invalid] [--validate-only]
```

| Option | Meaning |
| --- | --- |
| `-i`, `--input` | Workbook or folder (default: `.`) |
| `--actual` | Explicit actual-results workbook |
| `-o`, `--output` | Report path (default: `bracket_report.xlsx`) |
| `--skip-invalid` | Skip malformed entrant files, with warnings |
| `--validate-only` | Parse and score, print a validation summary, write nothing |

CLI flags and scoring behavior are unchanged. CLI reports also use the
five-sheet format, so the Streamlit app can reopen them.

Exit codes: `0` success, `2` input/template/report error, `1` unexpected error,
`130` interrupted.

## Validation

- `VALIDATION.md` records the verified 63-slot map and the checks performed
  against the sample template.
- Run `python scorekeeper.py --input sample_data\demo --validate-only` to
  reproduce the template, seed, pending, and scoring checks.
- Run the test suite:

```powershell
pip install -r requirements-dev.txt
.\venv\Scripts\python.exe -m pytest -q
```

The tests cover the slot map, merged-cell parsing, discovery, actual-file
selection, template/seed failures, scoring weights, pending games, accuracy,
tie-breaks, competition ranks, report layout, the five-sheet contract, header
reordering, report round trips, seeded and legacy Teams contents,
State/Teams/Corrections contents, actual cascades, entrant correction logging,
overwrite protection, locked files, legacy report loading and rebuild gating,
local-folder scan/rebuild, input immutability, CLI exit codes, and a Streamlit
AppTest smoke flow covering the bracket board and winner toggle.

## Project layout

| Path | Purpose |
| --- | --- |
| `bracket/template.py` | 63-slot map, anchors, scoring weights, headers, normalization |
| `bracket/loader.py` | Grid/merged-cell reader, discovery, template validation |
| `bracket/scoring.py` | Per-game results, per-round scoring, pending logic, ranking, cascades |
| `bracket/report.py` | Five-sheet openpyxl report and atomic save |
| `bracket/store.py` | Report loading, corrections, folder scan, rebuild, save session |
| `app.py` | Streamlit UI |
| `scorekeeper.py` | CLI |
| `sample_data/demo/` | Actual-results and entrant fixtures |
| `tests/` | Pytest suite, including Streamlit AppTest |

## Environment

The `.env` pattern is preserved: `.env` is loaded with `override=False`, only
`.env.example` is committed, and real secrets remain gitignored. Copy
`.env.example` to `.env` to change `APP_NAME` or set `APP_ENV`/`API_KEY`. The
bracket core has no Streamlit dependency.
