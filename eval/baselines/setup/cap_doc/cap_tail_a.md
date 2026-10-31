
## 5. Cap policy that now holds for every row of Table 4

- cuRace vector-clock and scalar-clock: a 1,200 s tool cap, escalated to 5,400 s and 84,600 s for every row that timed out (X1b's passes), with the offline verdict step capped at 14,400 s; the rows that still end without a verdict are the ones listed in section 6 plus vector-clock `P9-atomicCAS` (TIMEOUT at 1,200 s stands, section 7).
- cuRace collector-only: every program was recorded under the 1,200 s cap (none hit it) and judged offline under 14,400 s, except `P9-atomicCAS`, judged under 84,600 s here; every non-sm_90 program has a verdict.
- racecheck: a derived cap of 600 s or 1,200 s; the four rows that reached it (`P4-graph-coloring-racy-large`, `P7-pathfinder`, `P9-knn`, `P9-tridiagonal`) were re-run at a fixed 84,600 s, so one TIMEOUT remains (`P4-graph-coloring-racy-large`).
- iGUARD: a derived cap of 120 s to 158 s; the four programs that reached it (P6 interkernel racy and fixed, `P9-atomicCAS`, `P9-knn`; 12 repetition rows) were re-run at 84,600 s, and the five P7 rows (haversine at 84,600 s; heartwall, mandelbrot, particlefilter, stencil1d at 5,400 s, which was enough), so no iGUARD row ends in TIMEOUT.
- HiRace: has no TIMEOUT row.
- SuperCollider: has no TIMEOUT row; its 16 ERROR rows are the sm_90 programs.

