# SC10_STRONG: strong conflicts on SuperCollider's ten HeCBench programs (X14)

Branch `eval/sc10-strong` (from `eval/sc-native-hecbench` 442ff8b1, the X11 final results). Analysis only: no recording, no GPU, no change to code or to existing results. Reproduce: `python eval/sc10_strong.py --root . [--old-ref origin/eval/cap-84600]` (prints the table, the per-configuration lines and the source file of every cell).

**Counting rule.** Inputs: the confirm files `eval/x_logs/x11/**/confirm/X11-<program>__cuvein__<mode>.json` (the files `eval/results/sc_native/summary.csv` cites). A *data-race pair* = one entry of the file's `raw` list (verdict RACE, `conflict_class` DR, deduplicated per run by `run_cuvein.py`); an *unordered-strong-conflict pair* = one entry of `raw_sc` (verdict SC, `conflict_class` SC), per `split_raw` in `eval/baselines/run_cuvein.py`. `raw` includes pairs whose `matrix_class` is `structural` (e.g. 603 of 3,397 over all 95 files), as the RACE verdict does. Three runs per cell where X11 has three; the cell shows one number when the runs agree (they do in every cell). `raw_sc` is empty in all 95 confirm files, and every `raw` entry has `strength` none.

## Table (pairs per program; races = data-race pairs, strong = unordered-strong-conflict pairs)

| program (label) | S2* races | S2* strong | scalar races | scalar strong | vector races | vector strong |
|---|---|---|---|---|---|---|
| atomicCAS (racy) | 4 | 0 | 2† | n/a† | n/a† | n/a† |
| dxtc2 (racy) | 196 | 0 | 193 | 0 | 193 | 0 |
| knn (racy) | 9 | 0 | 2 | 0 | 2† | n/a† |
| tridiagonal (racy) | 93 | 0 | 24 | 0 | 24 | 0 |
| expdist (racy) | 35 | 0 | 35 | 0 | 0† | n/a† |
| overlap (race-free) | 0 | 0 | 0 | 0 | 0§ | n/a§ |
| fpc (race-free) | 0 | 0 | 0§ | n/a§ | 0§ | n/a§ |
| gpp (race-free) | 0 | 0 | 0§ | n/a§ | 0§ | n/a§ |
| crs (race-free) | 9 | 0 | 0§ | n/a§ | 0§ | n/a§ |
| mr (race-free) | 0 | 0 | 0 | 0 | 0 | 0 |

`†` capped or no analysable run; `§` no confirm file exists (old cap-84600 row, X11 kept it); `n/a` = cannot be determined from the files. S2\* = X11's "collector-only mode" (see caveat 1).

- † atomicCAS scalar: TIMEOUT at 84,600 s after 60,000 of 60,003 kernels; the 2 pairs are the `report_ids` of `stageB/x11b-scalar-clock-atomicCAS-r1/partial.json` (no confirm file, class not recorded). atomicCAS vector: not run at the cap (X11 `summary.csv` note); the old row (`eval/results/cap-84600/baselines-cuvein.csv`) is TIMEOUT, 0 reports. knn vector: TIMEOUT at 84,600 s, 279 kernels, 2 `report_ids` in `partial.json`. expdist vector: TIMEOUT at 84,600 s, analysis of the 4-kernel prefix out of memory (108 GB), 0 reports.
- § overlap vector, fpc/gpp/crs scalar and vector: X11 re-ran none (same program as the artifact); the old cap-84600 rows are CLEAN with `reports_dedup` 0 (3 rows each). No confirm file, so a strong-conflict count is not in the files. overlap scalar is the X11 smoke run (`x11smoke-scalar-clock-overlap-r1`, 1 run) and is a confirm file.
- No S2\*, scalar or vector run with a confirm file was capped.

## Per configuration (cells marked n/a count as no pair)

- **S2\* (collector-only, chain-closure):** strong conflict and no data race: none. Races alone: racy-labelled 5/5 reported, race-free-labelled 1/5 (crs). With strong conflicts counted too: 5/5 and 1/5 (unchanged).
- **scalar-clock:** strong-and-no-race: none. Races alone: racy 5/5 (atomicCAS from the 2 capped-prefix pairs), race-free 0/5. With strong: 5/5 and 0/5.
- **vector-clock:** strong-and-no-race: none. Races alone: racy 3/5 (dxtc2, knn from the capped-prefix pairs, tridiagonal; atomicCAS and expdist have no pair), race-free 0/5. With strong: 3/5 and 0/5.

So counting strong conflicts changes no program in any configuration: every `raw_sc` is empty.

## Not determined / caveats

1. **S2.** X11's write-up has no "S2": it calls the column "collector-only mode". Its verdict runs are `stageA-chain-r{1,2,3}-<program>` (collector-only with chain closure, `chain=1` in the CSV notes). I found no `--co-async` or `--co-r3` in X11's logs or scripts, so these runs look like C6 (chain closure only), not S2 of `CO_CHAIN_B.md` (`--chain-closure --co-async --co-r3 off`); I did not verify the flags of the run itself. Column S2\* uses them. The plain collector-only runs (`stageA-x11-co-r*`) were not used. S2 proper was not re-run on the SuperCollider binaries.
2. Strong-conflict counts for capped or old-row cells are unknown, not zero; the per-configuration lines treat them as zero.
3. Pairs are per-run deduplicated pc pairs, not distinct source locations or distinct addresses.
