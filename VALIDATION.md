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
| Test suite | 52 tests passed |

## Reproduce

```powershell
.\venv\Scripts\python.exe scorekeeper.py --input sample_data\demo --validate-only
.\venv\Scripts\python.exe -m pytest -q
```

The test suite covers the slot map, anchors, merged-cell resolution, discovery,
actual selection and overrides, template/seed failures, all scoring weights,
pending logic, accuracy denominators, tie-breaks, competition ranks, report
shape and fills, atomic writes, input immutability, and CLI exit codes.
