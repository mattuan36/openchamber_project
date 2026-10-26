# 2026 template validation report

This report records the verified geometry and the checks run against the
bundled 2026 printable bracket fixture.

## Anchors

| Anchor | Cell / row | Value |
| --- | --- | --- |
| Entrant name | `A2` | `NAME:______________MATT_______________` |
| East label | `A6` | `EAST (Washington D.C.)` |
| West label | `Q6` | `WEST (San Jose)` |
| South label | `A40` | `SOUTH (Houston)` |
| Midwest label | `Q40` | `MIDWEST (Chicago)` |
| Final Four left pick | `H34` | `F4-1` |
| Final Four right pick | `J34` | `F4-2` |
| Champion pick | `I43` | `CH` |
| Champion label | `I44` | `2026 NCAA CHAMPION` |

The parser detects these anchors from content rather than hard-coding the
sample's row numbers. The canonical anchor rows are used only for the bundled
fixture and tests; runtime parsing rebuilds the slot geometry from the detected
anchors. Slot IDs, weights, and report labels remain the shared contract.
Merged ranges are expanded before detection, so merged title, name, region, and
champion-label cells resolve correctly.

## Game map

All 63 games are unique by slot ID and pick coordinate. The map is round-major
within each region order (East, West, South, Midwest), then Final Four and
Championship.

| Slot | Round | Region | Game | Pick cell | Points | Feeders |
| --- | --- | --- | ---: | --- | ---: | --- |
| `R64-E1` | Round of 64 | East | 1 | `D9` | 1 | - |
| `R64-E2` | Round of 64 | East | 2 | `D13` | 1 | - |
| `R64-E3` | Round of 64 | East | 3 | `D17` | 1 | - |
| `R64-E4` | Round of 64 | East | 4 | `D21` | 1 | - |
| `R64-E5` | Round of 64 | East | 5 | `D25` | 1 | - |
| `R64-E6` | Round of 64 | East | 6 | `D29` | 1 | - |
| `R64-E7` | Round of 64 | East | 7 | `D33` | 1 | - |
| `R64-E8` | Round of 64 | East | 8 | `D37` | 1 | - |
| `R64-W1` | Round of 64 | West | 1 | `N9` | 1 | - |
| `R64-W2` | Round of 64 | West | 2 | `N13` | 1 | - |
| `R64-W3` | Round of 64 | West | 3 | `N17` | 1 | - |
| `R64-W4` | Round of 64 | West | 4 | `N21` | 1 | - |
| `R64-W5` | Round of 64 | West | 5 | `N25` | 1 | - |
| `R64-W6` | Round of 64 | West | 6 | `N29` | 1 | - |
| `R64-W7` | Round of 64 | West | 7 | `N33` | 1 | - |
| `R64-W8` | Round of 64 | West | 8 | `N37` | 1 | - |
| `R64-S1` | Round of 64 | South | 1 | `D43` | 1 | - |
| `R64-S2` | Round of 64 | South | 2 | `D47` | 1 | - |
| `R64-S3` | Round of 64 | South | 3 | `D51` | 1 | - |
| `R64-S4` | Round of 64 | South | 4 | `D55` | 1 | - |
| `R64-S5` | Round of 64 | South | 5 | `D59` | 1 | - |
| `R64-S6` | Round of 64 | South | 6 | `D63` | 1 | - |
| `R64-S7` | Round of 64 | South | 7 | `D67` | 1 | - |
| `R64-S8` | Round of 64 | South | 8 | `D71` | 1 | - |
| `R64-M1` | Round of 64 | Midwest | 1 | `N43` | 1 | - |
| `R64-M2` | Round of 64 | Midwest | 2 | `N47` | 1 | - |
| `R64-M3` | Round of 64 | Midwest | 3 | `N51` | 1 | - |
| `R64-M4` | Round of 64 | Midwest | 4 | `N55` | 1 | - |
| `R64-M5` | Round of 64 | Midwest | 5 | `N59` | 1 | - |
| `R64-M6` | Round of 64 | Midwest | 6 | `N63` | 1 | - |
| `R64-M7` | Round of 64 | Midwest | 7 | `N67` | 1 | - |
| `R64-M8` | Round of 64 | Midwest | 8 | `N71` | 1 | - |
| `R32-E1` | Round of 32 | East | 1 | `E11` | 2 | R64-E1, R64-E2 |
| `R32-E2` | Round of 32 | East | 2 | `E19` | 2 | R64-E3, R64-E4 |
| `R32-E3` | Round of 32 | East | 3 | `E27` | 2 | R64-E5, R64-E6 |
| `R32-E4` | Round of 32 | East | 4 | `E35` | 2 | R64-E7, R64-E8 |
| `R32-W1` | Round of 32 | West | 1 | `M11` | 2 | R64-W1, R64-W2 |
| `R32-W2` | Round of 32 | West | 2 | `M19` | 2 | R64-W3, R64-W4 |
| `R32-W3` | Round of 32 | West | 3 | `M27` | 2 | R64-W5, R64-W6 |
| `R32-W4` | Round of 32 | West | 4 | `M35` | 2 | R64-W7, R64-W8 |
| `R32-S1` | Round of 32 | South | 1 | `E45` | 2 | R64-S1, R64-S2 |
| `R32-S2` | Round of 32 | South | 2 | `E53` | 2 | R64-S3, R64-S4 |
| `R32-S3` | Round of 32 | South | 3 | `E61` | 2 | R64-S5, R64-S6 |
| `R32-S4` | Round of 32 | South | 4 | `E69` | 2 | R64-S7, R64-S8 |
| `R32-M1` | Round of 32 | Midwest | 1 | `M45` | 2 | R64-M1, R64-M2 |
| `R32-M2` | Round of 32 | Midwest | 2 | `M53` | 2 | R64-M3, R64-M4 |
| `R32-M3` | Round of 32 | Midwest | 3 | `M61` | 2 | R64-M5, R64-M6 |
| `R32-M4` | Round of 32 | Midwest | 4 | `M69` | 2 | R64-M7, R64-M8 |
| `S16-E1` | Sweet 16 | East | 1 | `F15` | 4 | R32-E1, R32-E2 |
| `S16-E2` | Sweet 16 | East | 2 | `F31` | 4 | R32-E3, R32-E4 |
| `S16-W1` | Sweet 16 | West | 1 | `L15` | 4 | R32-W1, R32-W2 |
| `S16-W2` | Sweet 16 | West | 2 | `L31` | 4 | R32-W3, R32-W4 |
| `S16-S1` | Sweet 16 | South | 1 | `F49` | 4 | R32-S1, R32-S2 |
| `S16-S2` | Sweet 16 | South | 2 | `F65` | 4 | R32-S3, R32-S4 |
| `S16-M1` | Sweet 16 | Midwest | 1 | `L49` | 4 | R32-M1, R32-M2 |
| `S16-M2` | Sweet 16 | Midwest | 2 | `L65` | 4 | R32-M3, R32-M4 |
| `E8-E1` | Elite Eight | East | 1 | `G23` | 6 | S16-E1, S16-E2 |
| `E8-W1` | Elite Eight | West | 1 | `K23` | 6 | S16-W1, S16-W2 |
| `E8-S1` | Elite Eight | South | 1 | `G57` | 6 | S16-S1, S16-S2 |
| `E8-M1` | Elite Eight | Midwest | 1 | `K57` | 6 | S16-M1, S16-M2 |
| `F4-1` | Final Four | Final | 1 | `H34` | 8 | E8-E1, E8-S1 |
| `F4-2` | Final Four | Final | 2 | `J34` | 8 | E8-W1, E8-M1 |
| `CH` | Championship | Final | 1 | `I43` | 12 | F4-1, F4-2 |

## Checks performed

| Check | Result |
| --- | --- |
| Slot count | 63, with 63 unique IDs and 63 unique pick coordinates |
| Round counts | 32, 16, 8, 4, 2, 1 |
| Weights | 1, 2, 4, 6, 8, 12 |
| Maximum | 148 |
| Seed validation | East, West, South, and Midwest each contain seeds 1-16 |
| Sample picks | 63/63 filled; champion Arizona at `I43`; F4 Houston at `H34`, Arizona at `J34` |
| Sample self-score | 148, correct 63, pending 0, accuracy 100% |
| Demo actual (`2026_results.csv`) | `OFFICIAL`, 63/63 picks |
| Demo standings | MATT 148 (63/63); CHRIS 136 (62/63), championship wrong |
| Pending scenario | Blanking `CH` and `F4-1` gives 128 points, 61 correct, 2 pending, accuracy 100% |
| Merged-cell xlsx | Parsed 63/63 from an `.xlsx` with merged title, name, region, and champion-label ranges |
| Right team block | Both `P` and `Q` team-column variants parse 63/63 |
| Invalid entrant | Fails by default; `--skip-invalid` skips it and records a warning |
| Invalid actual | Always fails, even with `--skip-invalid` |
| Input immutability | SHA-256 digests unchanged before and after loading and report writing |
| Atomic report write | Successful `.xlsx` written through a temporary file; no temporary file left behind |
| Five-sheet report | `Picks`, `Standings`, `State`, `Teams`, `Corrections`; all five visible; no hidden state sheet |
| Report round trip | Saved and reloaded picks, entrants, corrections, and scores match |
| Derived Standings | Tampered ranks, totals, and accuracy in the workbook are ignored; scores are recalculated from Picks |
| Header reordering | Picks columns reversed after save; loading by header name recovers every pick |
| State contents | Schema, created/updated UTC, source folder, rules, app, format; no entrant names, picks, or source filenames |
| Teams contents | Exactly 32 R64 matchups with slot, region, both teams, and printed seeds; play-in labels keep both entrants and repeat the shared seed |
| Corrections contents | Timestamp, entrant, source file, slot, old/new pick, reason; entries survive reload |
| Seed round trip | Seeds for normal and play-in games survive save/reload and normalize into the board's team-to-seed map |
| Legacy five-sheet seeds | A four-column Teams sheet loads names-only with no seed map and a rebuild hint in Actual Results |
| Actual cascade/pending | Changing `R64-E1` to Siena clears impossible `R32-E1`, `S16-E1`, and `E8-E1` picks, raises pending to 3, and scores MATT 135 |
| Actual Results board | Three panels with East/South on the left, West/Midwest mirrored on the right, and Final Four/Championship in the center; R32/S16/E8 cards align with feeder spans |
| Winner toggle | Clicking a team highlights it; clicking the highlighted winner again clears the game back to pending |
| Entrant correction gate | Empty reason and invalid team are rejected; a valid correction is logged and reloads |
| Overwrite protection | Raw `.xlsx` target refuses to save and keeps its digest; saved report can be overwritten |
| Locked report | `os.replace` permission failure raises a clear message, keeps the in-memory edit, and leaves the saved report unchanged |
| Legacy report loading | A Picks/Standings-only report loads with legacy metadata and a warning; it is read-only and saving is refused until rebuilt from raw brackets |
| Local folder workflow | 3 raw files discovered, report produced, report detected separately, rebuild restores original actual picks; `~$` owner files and nested files are ignored |
| Report-only folder | A folder with only a saved report can still continue; rebuilding from raw files is refused |
| Team disagreement warning | An entrant with a different first-round matchup emits a warning and does not override the actual bracket |
| Fresh-session continue | An existing report loads automatically, with matching picks and scores |
| Save As sync | Saving to a new report path updates the active report and the editable Setup path |
| Top-bar shell | Setup, Results, Leaderboard, and Save/Load switch from the top segmented navigation; the sidebar is absent; report status and autosave live in the top-bar popover |
| Setup hierarchy | Folder scan, saved report, rebuild, and advanced paths render as one page; rebuild and advanced sections are collapsed when a saved report is open |
| Leaderboard bracket | Selecting a standings row renders that entrant's bracket with both teams per matchup and a result line; correct picks are green with a check, incorrect red with an X, and pending gray with a dash |
| Streamlit AppTest | Demo load, actual edit, winner toggle, seeded board and mirrored paths, leaderboard bracket selection, save, reload, Save As, and fresh-session continue all run without app exceptions |
| Test suite | 70 tests passed |

## Streamlit and five-sheet verification

Run the app locally:

```powershell
.\venv\Scripts\streamlit.exe run app.py
```

Verified flow:

1. The default folder `sample_data\demo` scans three raw bracket files and
   auto-selects `2026_results.csv` as the actual bracket.
2. Creating the report writes `bracket_report.xlsx` with five visible sheets
   and an empty Corrections sheet.
3. `sample_data\demo` scores MATT 148 and CHRIS 136, matching the CLI.
4. Actual Results renders the three-panel board. East/South read
   `R64 → R32 → S16 → E8`; West/Midwest read `E8 ← S16 ← R32 ← R64`. Every
   matchup shows seeds, the selected winner is highlighted, and later-round
   cards sit at the centers of their feeder spans.
5. Changing actual `R64-E1` from Duke to Siena clears the no-longer-possible
   `R32-E1`, `S16-E1`, and `E8-E1` picks, marks three games pending, and lowers
   MATT to 135 and CHRIS to 123. Clicking Siena again clears `R64-E1` to pending
   (four pending games); clicking it once more restores the three-pending state.
6. Saving and reloading the report preserves that edit, the seeds, and the
   recalculated standings. Corrections made through the advanced Save/Load
   control are logged and persist across reload.
7. The AppTest smoke test repeats this flow headlessly, including the board
   markup, winner toggle, Leaderboard bracket selection, and Save/Load page.

## Reproduce

```powershell
.\venv\Scripts\python.exe scorekeeper.py --input sample_data\demo --validate-only
.\venv\Scripts\python.exe -m pytest -q
```

The test suite covers the slot map, anchors, merged-cell resolution, discovery,
actual selection and overrides, template/seed failures, all scoring weights,
pending logic, accuracy denominators, tie-breaks, competition ranks, per-game
results and cascades, five-sheet report shape and fills, header reordering,
report round trips, seeded and legacy Teams contents, State/Teams/Corrections
contents, entrant correction logging, atomic writes, overwrite and locked-file
handling, legacy report loading, local-folder scan and rebuild, input
immutability, CLI exit codes, and the Streamlit AppTest workflow.
