# T21b triage: llamacpp-2, llamacpp-4, llamacpp-5

Jeffery's decision (2026-10-22): the three llamacpp targets go to triage; amrex-1 and hecbench-hungarian-1 stay m4
(a later reanalysis of those two is reported separately). Runtime: cuVein f551ca0 (libsanalyzer 5a20fd14, collector
b746b4dd, fatbin a2d7368b), the recordings of the main flavor in `realworld-2026-10` (none re-recorded). Harness:
`study/realworld-recall` at 0d30817 (`run_cuvein.py` tries the dots that name the kernel first). CPU jobs on
`normal`: 319189 (llamacpp-2, c45, 4 h 43 min), 319190 (llamacpp-4, c47, 1 h 40 min), 319178 (llamacpp-5
re-attribution, c22, 51 min). Logs: `eval/x_logs/t21b-triage-reanalyze-llamacpp-{2,4}-*.log`,
`analyze-main-llamacpp-*.out`, `attrib-main-llamacpp-*.out`.

## Cause of the ERROR rows (llamacpp-2, llamacpp-4)

Not a detector failure. `run_cuvein._analyze_reports` tried every `.dot` of the program, in sorted order, for each
kernel JSON until one aligned; a wrong dot is rejected only after a full `sync_dominance.analyze` parse. llamacpp
builds ship many large dots (one per CUDA source file), so the search alone ran past `--analysis-timeout 3600` and
the row was ERROR (scored m4). Measured on llamacpp-4 (`~/triage_llama/ana.py`, removed): with only the dot that
names the kernel (`softmax.sm_89.dot`) the prefilter takes 0.3 s and the analysis 10.8 s per mode, with the verdicts
of the full search. Fix 0d30817 orders the dots (those whose text names the kernel's base identifier first, then the
rest in the original order); a wrong dot still raises `AlignmentError` and the loop moves on, so the verdicts are
those of the unfiltered search, reached sooner. Results are unchanged by construction; only time changes.

## Per target

### llamacpp-2 (oracle kernel `mm_ids_helper`, `mmid.cu`, DR)

- **Buggy, both modes: RACE, DETECTED.** 2 reports, both at the oracle sites: shared RAW `0x6d0 -> 0x1220` and
  `0x760 -> 0x1220` (STS `mmid.cu:96` -> LDS `mmid.cu:106`), class structural, `a2` robust, not uncertain. The
  oracle kernel was seen in 1 of 3 kernel JSONs; 0 unaligned; the dot matches the regenerated dot.
- **Fixed, both modes: CLEAN.** The same two site pairs (shifted to `0x1230` by the added barrier) are ORDERED,
  class barrier-ordered; 0 reports. Expected outcome after rescoring: CLEAN-FOR-PAIR. (At 3423e21 the fixed rows
  were NOT-SCORED only because `attrib/llamacpp-2-fixed.json` was written at 00:01 on 10-23, after that scoring run.)
- **Score effect:** DR miss -> DETECTED (both modes); fixed NOT-SCORED -> CLEAN-FOR-PAIR.

### llamacpp-4 (oracle kernel `soft_max_f32`, `softmax.cu`, DR)

- **Buggy, both modes: RACE, DETECTED.** 1 report, shared WAR `0x870 -> 0xa20` (LDS `common.cuh:643` via
  `softmax.cu:102` -> STS `common.cuh:638`), class structural, at the oracle pair. The two neighbouring oracle site
  pairs (`0x850 -> 0x870`, `0xa20 -> 0xa60`, RAW) are ORDERED (block barrier), as the oracle expects; 4 read-read
  pairs skipped.
- **Fixed, both modes: CLEAN.** All three oracle site pairs ORDERED (`0x870 -> 0xa30` is now barrier-ordered);
  0 reports. The earlier fixed row was NOT-SCORED because that job hit its 5 h limit inside the dot search.
- **Score effect:** DR miss -> DETECTED (both modes); fixed NOT-SCORED -> CLEAN-FOR-PAIR. Already reflected in
  `recall.csv` at 3423e21.

### llamacpp-5 (oracle kernel `ssm_scan_f32`, `ssm-scan.cu`, DR)

- **Buggy, both modes: RACE, DETECTED** (was MISSED, m1/m3 proposed). The detector verdict never changed: 264
  races, all structural, in both the old and new attribution. The miss was a stale attribution: the scored
  `attrib/llamacpp-5-buggy.json` (16:27 on 10-22) was produced before the D-T2 attribution-parser fix and has
  `a_frames`/`b_frames` null and an empty `site_verdicts`, so no report could be matched to the oracle's sites. The
  re-attribution with the fixed parser (319178) has frames on every report and 16 oracle site pairs, all RACE,
  structural: shared WAR `0xee0/0x1030/0x10b0/0x1200 -> 0xca0`, `0xf20/0x1070/0x1190/0x12b0 -> 0xcb0` and the 8
  matching RAW pairs; 10 read-read pairs skipped. The new JSON replaces the stale one in `attrib/`.
- **Fixed, both modes: CLEAN, CLEAN-FOR-PAIR** (unchanged): the same 16 site pairs (shifted by `0x10`) are ORDERED.
- **Score effect:** DR miss -> DETECTED (both modes). The m1/m3 proposal for llamacpp-5 is withdrawn.

## Net effect on the main flavor (buggy builds, DR component)

All three llamacpp targets become DETECTED in both modes, and all three fixed builds CLEAN-FOR-PAIR. The DR row
moves from 19 detected / 4 missed to 22 detected / 1 missed; the remaining DR miss is amrex-1 (final m4 unless its
reanalysis and re-recording change it).

## Side defect (cosmetic, not fixed)

`eval/baselines/parallel.py` lines 296-299 build the pc -> line map with `pcmap.update(...)` over every cubin of the
executable. PCs are per-cubin offsets, so a pc present in several cubins keeps the line of the last cubin. The CSV
column `report_lines` is therefore wrong for multi-cubin builds: llamacpp-4 buggy reports `fattn-tile.cuh:1131` for a
`softmax.cu` race. Scoring does not use that column (attribution resolves frames per kernel from the kernel's own
cubin and dot), so no outcome changes. Fix: key the map by (cubin, pc), or resolve lines through the kernel's cubin.
