# 2026 March Madness Bracket Scorekeeper

A command-line scorekeeper for the 2026 printable NCAA men's bracket. It reads
one or more filled bracket workbooks, scores every entrant against an actual
results workbook, and writes a formatted two-sheet Excel report.

This phase delivers the reusable loader, scoring engine, report writer, and
CLI. It does not build the Streamlit results-entry dashboard yet; `app.py` is
left untouched for that later phase.

## Quick start

Python 3.10 or newer is required.

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Score the bundled demo and write bracket_report.xlsx
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

## Input rules

- Accepts `.xlsx`, `.xlsm`, or `.csv` (CSV is a preview format).
- A folder is scanned non-recursively. A single workbook can also be passed.
- The actual-results workbook is the one whose filename contains `results`
  (case-insensitive). Use `--actual PATH` when the filename does not contain
  it or when more than one candidate exists.
- Every workbook must be the 2026 printable bracket template. The loader finds
  the `NAME:` cell, the EAST/WEST/SOUTH/MIDWEST labels, the round headers, and
  `2026 NCAA CHAMPION`, then maps all 63 games from that geometry.
- The actual-results file is validated strictly. Malformed entrant files stop
  the run unless `--skip-invalid` is used.
- The upper printable bracket is authoritative. The lower duplicate picks
  block is not read.
- Input workbooks are only read; the scorekeeper never modifies them. A report
  path that resolves to an input file is rejected.
- The report default is `bracket_report.xlsx`; report names containing
  `results` are rejected so they cannot be mistaken for an actual-results file.

### Parsing the visual bracket

The bracket is not treated as a flat table. The parser:

1. Loads the worksheet grid.
2. Resolves merged ranges by filling the merged value into every cell of the
   range.
3. Detects anchors and validates the template's seed layout (1-16 in each
   region).
4. Maps each of the 63 games to its pick cell.
5. Splits play-in labels such as `Texas/ NC State` and validates that picks are
   real teams and consistent with their feeder games, emitting warnings rather
   than silently guessing.

The right-hand team block is detected from the populated cells, so both the
`P`-team and `Q`-team variants of the printable template work.

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
A blank entrant pick is worth zero once the actual game is decided and does
count as a miss. Accuracy is `correct picks / decided games`, not
`correct picks / 63`.

## Report

### Picks

- Row 1 is the header; row 2 is the actual-results row; entrant rows follow in
  standings order.
- Column A is the source filename and column B is the entrant name.
- Columns C through BM are the 63 games, in round-major order and labelled by
  round, region, and game number (for example `R64 East 1`, `S16 West 2`,
  `F4 Game 1`, `Championship`).
- Green = correct, red = incorrect, gray = pending. The actual row uses a dark
  blue reference fill.
- The header row and the Source File/Entrant columns are frozen, and the sheet
  has an autofilter.

### Standings

The sheet shows rank, entrant, source file, points in each round, total,
correct picks, pending games, and accuracy. The Total column has a data bar,
and the top three ranks are highlighted.

Ties are broken by total points, then championship, Final Four, Elite Eight,
Sweet 16, Round of 32, and Round of 64 correct picks, then entrant name. Tied
entrants share a competition rank (`1, 2, 2, 4`).

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

The tests cover the slot map, merged-cell parsing, discovery and actual-file
selection, validation failures, all scoring weights, pending games, accuracy,
tie-breaks, competition ranking, report layout and fills, atomic writes, input
immutability, and every CLI path.

## Project layout

| Path | Purpose |
| --- | --- |
| `bracket/template.py` | 63-slot map, anchors, scoring weights, normalization |
| `bracket/loader.py` | Grid/merged-cell reader, discovery, template validation |
| `bracket/scoring.py` | Per-round scoring, pending logic, ranking |
| `bracket/report.py` | Two-sheet openpyxl report and atomic save |
| `scorekeeper.py` | CLI |
| `sample_data/demo/` | Actual-results and entrant fixtures |
| `tests/` | Pytest suite |
| `app.py` | Existing Streamlit starter, intentionally unchanged |

## Environment and future dashboard

The existing `.env` pattern is preserved: `.env` is loaded with
`override=False`, only `.env.example` is committed, and real secrets remain
gitignored. The core `bracket` modules have no Streamlit dependency, so a later
dashboard can import `parse_bracket`, `score_all`, and `write_report` directly
to enter and save actual results. No dashboard work is included in this phase.
