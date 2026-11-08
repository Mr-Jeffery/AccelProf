# lock_rtraw: why C6 (collector-only + chain closure) judged the pair ORDERED while scalar-clock reported it

C6b step 0. Program `P5-race_interblock_none-lock_rtraw`, kernel `_Z5kmainPVj`; the pair is `global:0x170-0x2f0:WAW` (the one in `eval/results/co-chain/step3/detect/sc_only_pairs_classified.csv`, disposition "edge; judged ORDERED(,edge)"). Analysis only: no recording, no python edit.

## Commands

    sbatch eval/baselines/setup/c6b_rtraw.sbatch
    # jobs 326237 (first run: its dot lookup skipped the dot, so only the P6 section is valid) and 326247 (final), normal --exclusive
    # runs: /home/fzheng4/AccelProf/.env/bin/python eval/baselines/setup/c6b_rtraw.py
    #   CUVEIN_HOME=ACCEL_PROF_HOME=/home/fzheng4/wt-c6b, python/ taken from `git archive be325e03 python` (read-only; wt-c6b/python is being edited by another agent)

`c6b_rtraw.py` calls `sync_dominance.analyze(dot, kernel_json, chain_closure=True)` on the collector-only recording and `analyze(dot, kernel_json)` on the scalar-clock recording (the calls `run_cuvein.py:132` makes), with loggers around `HBGraph.chain`, `_past_release`, `_before_acquire` and `ordered`. Log of the final job: `eval/results/co-chain-b/step0/c6b_rtraw_326247.log`.

Inputs (store `/mnt/beegfs/fzheng4/cuvein_traces`):
- collector-only: `final-2026-11-co/P5-race_interblock_none-lock_rtraw/collector-only/kernel_0.json`
- scalar-clock: `final-2026-11/P5-race_interblock_none-lock_rtraw/scalar-clock/kernel_0.json`
- CFG (identical in both): `.../dots/race_interblock_none-lock_rtraw.sm_89.dot`
- C6 raw record: `eval/results/co-chain/c1-main/confirm/P5-race_interblock_none-lock_rtraw__cuvein__collector-only.json`. Its `raw_sc` holds only the other pair (0x340 vs 0x140, `chain_src` "chain", `chain_path` 0x140, 0x2c0, 0x340, verdict SC; the CSV notes say `classes=sc:1;chain=1;chain_hops=8;chain_derived=1`). The 0x170/0x2f0 pair is not in the raw record because its verdict is ORDERED (judged, not reported); it is in the verdict step's `verdicts` list, below.

## Kernel (pcs from the dot)

    arm A (entry branch at 0x40):  0xb0  ATOMG.E.CAS.STRONG.GPU   lock acquire (spin 0xc0/0xd0)
                                   0x110 MEMBAR.SC.GPU ; 0x140 LDG.E.STRONG.SYS (read)
                                   0x170 STG.E (write, inside the section)
                                   0x180 MEMBAR.SC.GPU ; 0x1b0 ATOMG.E.EXCH.STRONG.GPU   unlock ; 0x1c0 EXIT
    arm B (.L_x_0 at 0x1d0):       0x230 ATOMG.E.CAS.STRONG.GPU   lock acquire (spin 0x240/0x250)
                                   0x290 MEMBAR.SC.GPU ; 0x2c0 LDG.E.STRONG.SYS (read)
                                   0x2f0 STG.E (write, inside the section)
                                   0x300 MEMBAR.SC.GPU ; 0x330 ATOMG.E.EXCH.STRONG.GPU   unlock
                                   0x340 STG.E.STRONG.SYS (write AFTER the unlock: the "rtraw" part)

dot snippet (block edges): `"_Z5kmainPVj":exit0:e -> ".L_x_0"`, `"_Z5kmainPVj":exit0:s -> "BB0"`, `"BB0" -> ".L_x_2"`, `".L_x_2":exit0:e -> ".L_x_2"` (spin of 0xb0), `".L_x_2":exit0:s -> "BB1"`, `"BB1" -> ".L_x_1"` (0xf0..0x1b0); `".L_x_0" -> ".L_x_4"`, `".L_x_4":exit0:e -> ".L_x_4"` (spin of 0x230), `".L_x_4":exit0:s -> "BB2"`, `"BB2" -> ".L_x_3"` (0x270..0x350).

## Recorded edges (current <- ancient, distance, count)

Collector-only (final-2026-11-co):

    0x2f0 <- 0x170 grid 1      0x230 <- 0xb0  grid 1     0x230 <- 0x1b0 grid 1   (the hop that lands on arm B's CAS)
    0x1b0 <- 0x230 grid 1      0x230 <- 0x230 thread 3   0x330 <- 0x230 thread 1
    0x2c0 <- 0x140 grid 1      0x340 <- 0x2c0 thread 1

Scalar-clock (final-2026-11):

    0x2f0 <- 0x170 grid 1      0x230 <- 0xb0  grid 1     (no 0x230 <- 0x1b0)
    0x1b0 <- 0x230 grid 1      0x230 <- 0x230 thread 3   0x330 <- 0x1b0 grid 1   (the unlock hop lands on arm B's UNLOCK)
    0x2c0 <- 0x140 grid 1      0x340 <- 0x2c0 thread 1
    trace points: release_points {0x170: [0x1b0], 0x140: [0x1b0], 0x2f0: [0x330], 0x2c0: [0x330], 0x340: []}
                  acquire_points {0x2f0: [0x230], 0x170: [0xb0], 0x2c0: [0x230], 0x340: [0x330], 0x140: [0xb0]}

## C6's verdict for the pair, and the certificate

Verdict step on the collector-only recording:

    ordered(cur=0x2f0, anc=0x170, d=3 [grid]) -> strength=0 (R1 none), coh=0 (R2 none), chain=['0x1b0','0x230']
    verdict: {"current_pc":752,"ancient_pc":368,"race_type":"WAW","observed_distance":"grid","strength":"none",
              "hb_chain":["0x1b0","0x230"],"hb_class":null,"verdict":"ORDERED","chain":false,"chain_rescue":false}

- Certificate: **R3, the PC-level atomic hand-off chain** (`HBGraph.chain`), `hb_chain` 0x1b0 -> 0x230. R1 (dominance) and R2 (coherence) give nothing. `chain: false` means the pair came from a recorded edge (0x2f0 <- 0x170), not from the closure; the closure produced only the other pair (0x140/0x340, below).
- Release point: **0x1b0**, arm A's unlock `ATOMG.E.EXCH.STRONG.GPU`, after the `MEMBAR.SC.GPU` at 0x180. Collector-only has no trace release points, so `chain` uses the region rule: an atomic `a` with `release_scope(0x170, a) > NONE`, here 0x1b0 with scope GPU, which covers the observed grid distance.
- Acquire it lands on: **0x230**, arm B's lock CAS (hop 0x1b0 -> 0x230 from the edge `0x230 <- 0x1b0`); 0x230 dominates 0x2f0 in program order.
- Gates passed: `_before_acquire(u=0x170, rel=0x1b0)` False (0x170 is after its own acquire); `_past_release(acq=0x230, cur=0x2f0)` False (the acquire is a CAS and no atomic on its location lies between 0x230 and 0x2f0).

## What scalar-clock declined on

Scalar-clock's verdict for the same pair: RACE (`hb_chain` null, `hb_class` null, strength none, coherence none).

    chain(anc=0x170, cur=0x2f0) -> None ; chain(anc=0x2f0, cur=0x170) -> None
    _before_acquire(u=0x170, rel=0x1b0) -> False ; _past_release never reached for this pair

- It did NOT decline on `_past_release` (the landing check) or on `_before_acquire` (write-before-lock): neither fires for 0x170/0x2f0, in either mode.
- It declined because `chain` finds no landing. Scalar-clock's dump has trace points: the release point of 0x170 is `[0x1b0]` and the acquire point of 0x2f0 is `[0x230]`, so the chain must start at 0x1b0 and land exactly on 0x230 (`_chain_from(..., land=0x230)`, and every acquire point must be covered). Its recording has no edge `0x230 <- 0x1b0`; the hop leaving 0x1b0 is `0x330 <- 0x1b0` (arm B's unlock), which is after 0x2f0 in program order and is not 0x230. No chain covers the acquire point, so `chain` returns None: no static proof, and a race verdict.
- The difference between the two recordings is the lock order: in the collector-only run arm B's CAS observed arm A's unlock (`0x230 <- 0x1b0`); in the scalar-clock run it did not (`0x330 <- 0x1b0`). In addition, collector-only has no trace release/acquire points, so its chain is found by region dominance (some hop from 0x1b0 reaches an atomic that dominates 0x2f0), while scalar-clock requires the landing atomic to be the recorded acquire point.
- Not determined by the recordings (no addresses, no thread ids, no order in either JSON): why the two runs ordered the lock differently. They are different runs; which of the two effects (schedule or the trace-point rule) alone would have flipped the verdict was not tested (that needs the collector-only chain with the scalar-clock edges or vice versa).

The other pair of the program, 0x140 (LDG) against 0x340 (STG after the unlock), is where `_past_release(acq=0x230, cur=0x340)` returns True in the collector-only run and `_past_release(acq=0x330, cur=0x340)` True in scalar-clock's: chain None in both modes, verdict SC in both (in C6 this is the `classes=sc:1` record, reached by the closure through 0x140 -> 0x2c0 -> 0x340).

## P6-memcpy-shared_readwrite_race-racy (F4): the recorded edge

Collector-only kernel JSON (`final-2026-11-co/P6-memcpy-shared_readwrite_race-racy/collector-only/kernel_0.json`, kernel `async_race_kernel`): nodes 0x70 (READWRITE GLOBALSHARED), 0x90 (READ SHARED), 0xb0, 0xc0, 0xd0; edges `0x90 <- 0x70` with `intra_thread` 64 and every other distance field 0, `0xb0 <- 0x90` intra_thread 64, 0x70, 0xc0 and 0xd0 cold. Opcodes from the dot: 0x70 `LDGSTS.E` (the cp.async), 0x90 `LDS` (the read), 0xa0 `DEPBAR.LE` (the wait, after the read). The collector-only JSON has no `hb_async` key; the scalar-clock JSON of the same program has `hb_async` (and `hb_events_count`, `hb_exits`, ...). The edges are the same in both recordings.
