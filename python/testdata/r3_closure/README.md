# r3_closure — X4's A2-inverted rtraw recordings (T23)

Inputs of `test_r3_landing_closure_on_the_a2_inverted_rtraw` (python/test_sync_dominance.py) and
of eval/R3_CLOSURE.md. Nothing here was re-recorded: the files are X4's own (eval/FINAL_RTRAW.md
section 6; X4 merged into cuVein as afccba7).

| file | copied from | sha256 |
|---|---|---|
| `scalar_clock_c58_run20.json` | `eval/results/final-rtraw/scor-scalar-clock/c58/run20/kernel_0.json` | `ecb46fa5359cfbe13f2ec6e0dbe4878c383ffdd83500f284fea61c92a6bfdb5c` |
| `vector_clock_c58_run3.json` | `eval/results/final-rtraw/scor-recorded/c58/run3/kernel_0.json` | `66a288fc43f795ccbce71c96b2977255ed021988141283e4b62443c017ac796b` |
| `race_interblock_none-lock_rtraw.sm_89.dot` | `/mnt/beegfs/fzheng4/cuvein_traces/final-rtraw/scor-scalar-clock/c58/cfg/race_interblock_none-lock_rtraw.sm_89.dot` (byte-identical to the `scor-recorded/c58/cfg` one; SLURM job 314781) | `ca6d2a97d2430ba8fff35ec4f15d56335d7a7e2fe0a9244af551b55118fd8d75` |

Both dumps are schedule C of FINAL_RTRAW.md section 5 (block 0's winning CAS is recorded before
block 1's unlock): the lock word's atomic edges are 0xb0->0x230, 0x230->0x230, 0x230->0x1b0,
0x1b0->0x330. The racy pair is block 1's read 0x140 against block 0's write 0x340 after its own
unlock (pcs 320 / 832 in the dumps' `hb_sync_pass`). Both dumps carry `hb_events` (the records
path) and `hb_sync_pass` / `hb_rmw_points` (the aggregates path).
