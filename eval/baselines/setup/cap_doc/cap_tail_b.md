## 7. Not re-run

- **cuRace vector-clock `P9-atomicCAS`**: excluded by Jeffery's rule. The scalar-clock row is TIMEOUT at 84,600 s (60,000 kernels, 1.1 GB); the vector-clock run at 84,600 s was killed for memory (ERROR, 15,229.6 s, 30,000 kernels, 189.6 GB, rc 1; `eval/results/final-b-24h-kept-vc/dropped.txt`), so the three TIMEOUT rows at 1,200 s (0 kernels, 96 to 100 GB) stand.
- **Rows already TIMEOUT at 84,600 s**: vector-clock `P9-expdist` (0 kernels, 21.0 GB) and `P7-stencil1d` (117 kernels, 98.5 GB); scalar-clock `P9-atomicCAS` (60,000 kernels) and `P7-stencil1d` (435 kernel JSONs, the last cut mid-write, 168.1 GB). Not repeated (section 6).
- **`P9-mr-cuda` under racecheck and iGUARD**: ERROR, a usage message with `native_rc=1` (an argument problem of the program's command line), not fixed; neither tool has a verdict on it.
- **The 16 sm_90 cuHadron programs** (`P6-bulkcpy-*`, `P6-dsmem-*`): ERROR on every cuRace mode, racecheck, iGUARD and SuperCollider (the GPUs here are sm_89 and sm_86); not run.
- **cuRace vector-clock `P7-particlefilter`**: called TIMEOUT without running at 84,600 s (Jeffery, 2026-10-30): it did not fit in memory on any target host (X1 on c64, 202 GB: 3 repetitions killed at 185.3 GB after 5,313 to 5,331 s; X1b on a 135 GB host: 124 to 125 GB at the 5,400 s cap; only kernels 0 to 2 of the first frame completed). The row carries the note "not run at cap=84600; memory"; its `peak_mb` (185,300) is X1's, not a new measurement.

## Commands

```
# merge (CPU job; normal partition)
python eval/baselines/setup/cap_merge.py            # -> eval/results/cap-84600/*.csv, newkeys.json, merge_log.txt, dropped.txt
bash   eval/baselines/setup/cap_tables.sh           # old and new sandboxes: make_tables.py --collector-only, co_tables1, cap_cells.py
python eval/baselines/setup/cap_report.py  > cells.md    # section 2
python eval/baselines/setup/cap_report2.py > rest.md     # sections 1, 3, 4, 5, 6
# collector-only atomicCAS: eval/x_logs/x7b_atomiccas.sbatch  (Part A ea98fef, store final-2026-11-co, --analysis-timeout 84600 --analysis-workers 16)
# vector-clock haversine analysis_s: eval/x_logs/x7b_hav.sbatch
```
