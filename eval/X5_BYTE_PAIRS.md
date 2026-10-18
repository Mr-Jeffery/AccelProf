# X5 byte pairs: what orders the 65 barrier-ordered pairs X5 binned as `other`

Branch `eval/x5-byte-pairs`, worktree `/home/fzheng4/wt-x5-byte-pairs`, **cut from
`eval/x5-static-dynamic` 1a2f1da** (X5). Left unmerged; nothing pushed. Investigation only: no change
to `sanalyzer/`, `nv-compute/`, `python/` or any X5 script; no GPU, no new recording; every job ran in
partition `normal`. Legend as in CLAUDE.md A4: **proved-in-effect** = checked over every row stated;
**tested** = a specific result asserted; **unverified** = said so.

## 0. Findings first

1. **No pair of the 65 is a possible missed race (c).** The 64 byte-wide pairs are **(b) a binner
   miss**; the ORDERED verdict is correct. The cp.async pair is **(a) a correct ORDERED verdict**.
2. **A missed-race mechanism outside these pairs, for Jeffery before X3** (§4). When a warp is
   diverged at a `WARPSYNC`, it executes the instruction in several groups and the trace gets one
   `syncwarp` record per group. Each record has `sync_mask` 0xffffffff and a partial `active_mask`.
   HbClock and the oracle join **all** `sync_mask` lanes at **each** record
   (`sanalyzer/src/tools/pc_dependency_analysis.cpp:1661-1668`, `python/hb_oracle.py:672-677`). The
   proof's model does the same (`design/proof/hb_proof.tex:145`: "a syncwarp arrival is an instance by
   itself"), and its trusted base states the release condition for barriers only (A3, `:206-208`). So a
   lane that has not arrived yet gets its pre-barrier accesses ordered after the arrived lanes'
   pre-barrier accesses.
   - **In these recordings it changes no reported pair:** 0 race pc pairs differ in all 60
     (program, mode) recordings, once each partial instance is merged into one record at its true
     completion.
   - **It does hide real races:** with the first `__syncwarp()`'s records removed (the trace the
     program would give without that call), the per-record join hides the clear/set WAW of 10 pairs,
     which the merged trace reports in 7–11 launches each.
   - **Corpus-wide effect: not measured.**
3. **The 64 byte-wide pairs** (P1 48, P3 16; 32 programs, 14 `cc_vertex_data` instantiations of
   ECL-CC; `__shared__ bool updated[warp]`). The kernel's `__syncwarp()` calls are compiled on sm_89
   to an instruction nvdisasm prints as **`NOP`**. Compute Sanitizer reports a syncwarp there
   (`SANITIZER_INSTRUCTION_SYNCWARP`). The NOP lies on every CFG path between the pair's two pcs, and
   HbClock joins the warp at it. X5's binner and R1 take syncs from opcode names (`BAR*`,
   `WARPSYNC`), so they see no barrier. "Byte-wide" is incidental: the flag is a `bool`.
   - **Evidence:** 13,013,400 conflicting instances in the records of 120 of the 128 rows. Every one
     is same-warp and has a syncwarp record holding **both** lanes in its active mask strictly between
     its two accesses: 0 uncovered, 0 cross-warp (proved-in-effect).
   - **The other 8 rows** (vector-clock, four 1296-node Persist programs) have no store with records;
     their scalar-clock rows, same binary, are covered.
4. **The cp.async pair** (P6 `memcpy-shared_writewrite_race-racy`, `LDGSTS` 0x70 -> `LDS` 0xb0).
   `cp.async.wait_all` and `__syncthreads()` are on its only path; R1 gives no credit by the T1a rule;
   the barrier-only clock orders it. The binner did list the barrier (`0xa0 BAR.SYNC`); `other` is
   X5's bin list having no case for an unconditional full barrier, which R1 certifies everywhere
   else. The program's labelled race, the copy/copy WAW at 0x70 (`shared_writewrite_race.cu:54`), is
   RACE in both modes.
5. **The brief's other candidates are ruled out** (§5).
   - Location granularity: HbClock, the oracle and the PCDG's shared shadow all key by the exact byte
     address.
   - Disjoint bytes of one word: the two accesses touch the same byte in 1,240 of 1,360
     launch-records, and no word is shared only through different bytes.
   - An inlined or predicated path: no. The missed sync is a straight-line NOP on every path. In 12
     kernels a `__syncwarp()` also has a `CALL`ed out-of-line helper, which the binner cannot see
     either, but the NOP stays on every u -> v path.
6. **Downstream** (§6). With the NOPs read as `WARPSYNC 0xffffffff`, X5's own binner puts all 64 pairs
   in `partial participation`, leaving `other` = 1. R1 then certifies the 32 NonPersist pairs
   (strength `warp`); the 32 Persist pairs stay `none` (syncwarps inside the grid-stride loop). X5's
   "no BAR or WARPSYNC anywhere in the kernel" holds for the printed SASS only, and its candidate "a
   word-granular edge against a byte-exact conflict check" is refuted. How many other kernels have
   syncwarps printed as NOP is **not measured**.

## 1. Inputs and method

* **Pairs.** X5's `eval/results/x5/barrier_ordered_pairs.csv` (unchanged from 1a2f1da), the 130 rows
  of bin `other` = 65 pairs x 2 modes.
* **X1 recording**, the one X5 binned: `final-2026-10-view/<id>/<mode>/kernel_*.json`. X1 ran with
  aggregates (X0). Its kernel JSONs carry `hb_races`, `hb_races_sync_only`, `hb_sync_pass`, the PCDG
  `edges` and `hb_stats`, but **no `hb_events`**, so no X1 record can be read.
* **Records** come from the newest older store that kept `hb_events` for the same program and mode
  and has **the same dot file (md5) as X1**. Search order: `t16-certain`, `t16-recorded-exits`,
  `t16-certain-exits`, `t12-after`, `t10-after`, `t9-after`, `evcand`, `t1a-p56`.
  - For a kernel with cp.async, the store's dumps must also carry X1's `hb_async` marker, which
    decides whether an LDGSTS replays as the issuing thread's agent
    (`python/sync_dominance.py:306-311`).
  - Result: `t16-certain` for all 120 byte rows; `t16-recorded-exits` for P6. `t16-certain`'s P6 dump
    has no `hb_async`, and neither has pipeline records (`eval/x_logs/x5b-p6-stores-314619.log`).
  - These are other recordings of the same binaries. X1's own facts are reported next to them per
    row.
* **Per row** (`x5b_byte_pairs.py`, job 314619):
  - *static*: the pcs on **every** instruction-level path u -> v (v unreachable from u once the pc is
    removed; X5's `CfgBinner.ins_reach`), among the kernel's NOPs and its
    `BAR*/WARPSYNC/DEPBAR/LDGDEPBAR`; X5's bin; X5's `CfgBinner.bin` and R1 (`HBGraph.ordered`) as
    printed and with those NOPs read as `WARPSYNC 0xffffffff`.
  - *X1*: per launch, the PCDG edge u -> v and its distance; whether `hb_races` /
    `hb_races_sync_only` / `hb_sync_pass` list the pc pair; `hb_stats`' clock bases.
  - *records*: the sync records at the cutting pcs; whether u and v touch the same byte, and how many
    (block, word) pairs they share only through different bytes.
  - *instance check* (`x5b_partial.instance_check2`, job 314625): every conflicting instance = an
    access at u by lane a, a later access at v by lane b != a, same block, same byte. For a's latest
    access at u before b's at v (a's earlier ones precede it in a's program order), is there a
    syncwarp record of that warp strictly between them in trace order? Recorded separately: whether
    some such record has **both** lanes in its active mask.
  - *counterfactual*: `hb_oracle.analyze`, the specification HbClock matches bit for bit
    (CLAUDE.md A4), on the records as recorded and with the cutting pc's sync records removed.
    Reported: the pair in `races` / `races_sync_only`, and every `races_sync_only` pair ending at u or
    v.
* **Replays without the global records** (`--shared-only`). The full replay of the 1296-node ECL-CC
  traces was OOM-killed at 94–120 GB RSS (job 314529): the oracle's dense clocks grow through the
  kernels' `atomicMax` / `atomicAdd` chain joins. The barrier-only clock takes no atomic join, and a
  shared location's buckets hold only shared records, so its answer on a shared pair cannot change.
  - **Checked against full replays (jobs 314474 / 314529) on the 104 byte rows that fit in memory:**
    identical barrier-only answers, vector-clock answers and trace facts in all 104
    (`eval/results/x5b/shared_only_check.md`).
  - The two P6 rows differ only because the full replay picked `t16-certain`, the pre-T1a dump; the
    store rule above was added after that run.
* `x5b_summary.py` decides each row's mechanism from these facts alone (rule in its docstring):
  **128 `syncwarp-as-NOP`** (120 with records + the 8 vector-clock rows' facts from their scalar-clock
  twins) and **2 `async+barrier`** (`eval/results/x5b/byte_pairs_tables.md`).

## 2. The 64 byte-wide pairs

### 2.1 The code

All 14 sources (`corpora/Indigo3Suite/generatedCodes/CUDA/CC-CUDA/<name>.cu`, job 314546) have this
shape, e.g. `CC_CUDA_V_Data_Pull_Determ_IntType_NonPersist_RaceBug_Warp_…cu:76-94`:

```
__shared__ bool updated[ThreadsPerBlock / WarpSize];   // :76
if (lane == 0) updated[warp] = false;                   // :79   STS.U8 by lane 0       (u of WAW)
__syncwarp();                                           // :80   NOP  0x150
for (int i = beg + lane; i < end; i += WarpSize) {     // :81
  ... if (d > new_label) { d = new_label; updated[warp] = true; }   // :88  STS.U8 (v of WAW, u of RAW)
}
__syncwarp();                                           // :93   NOP  0x780
if (updated[warp]) { ... }                              // :94   LDS.U8                 (v of RAW)
```

* **The two pairs per program:** WAW (clear -> set) and RAW (set -> read). The address register is
  `threadIdx.x >> 5`, so a warp's lanes share one byte and different warps use different bytes.
* **Persist variants** wrap this in a grid-stride loop and add a third `__syncwarp()` at the end of
  its body (e.g. `…Determ_IntType_Persist_RaceBug_Warp_…cu:107`).
* **The P1 `…NonPersist_RaceBug_Warp…-100n` kernel in SASS** (X1 dot, md5 `09d6cf420c1a`, identical in
  the seven stores checked, `eval/x_logs/x5b-probes-*.log`):

```
0140:   @!P0 STS.U8 [R7], RZ ;        u of the WAW pair (P0 = lane != 0)
0150:   NOP ;                          __syncwarp(): 760 syncwarp records, mask 0xffffffff
0320:   @P2 STS.U8 [R7], R13 ;        v of WAW / u of RAW (loop .L_x_4)
0770:   BSYNC B0 ;
0780:   NOP ;                          __syncwarp(): 760 syncwarp records
0790:   LDS.U8 R7, [R7] ;             v of the RAW pair
```

* **No kernel has a `BAR` or `WARPSYNC` as printed** (all 128 rows).
* **In 12 of the 14 kernels a `__syncwarp()` also has a non-converged path:** a convergence test
  (`BRA.CONV ~URZ`) skips a `CALL.REL.NOINC $__internal_0_$__cuda_sm70_warpsync`. The helper's body is
  `WARPSYNC 0xffffffff` in the 5 NonPersist kernels with a call and `WARPSYNC R<n>` in the 7 Persist
  ones; the two Pull NonPersist RaceBug kernels have no call. Example: P3 `…Determ_NonPersist_Atomic…`,
  `0700 BRA.CONV`, `0720 CALL`, helper `10a0 WARPSYNC 0xffffffff`, return to `0730 NOP`
  (`eval/x_logs/x5b-calls-314624.log`; Appendix B lists all 14). The cutting NOP stays on every
  u -> v path either way (the cut test of §1).

### 2.2 Why the barrier-only clock does not list the pair

1. **Collector.** The HB path patches `SANITIZER_INSTRUCTION_SYNCWARP` with `SyncwarpCallback`
   (`nv-compute/src/compute_sanitizer.cpp:309`): which SASS instructions are syncwarps is Compute
   Sanitizer's decision, not nvdisasm's opcode text. The dump writes `{"type": "syncwarp", "sync_mask":
   …, "active_mask": …}` (`pc_dependency_analysis.cpp:2519-2521`).
2. **Records.** Every cutting NOP carries syncwarp records with mask 0xffffffff in every recording
   (Appendix B).
   - Example: P1 `…NonPersist_RaceBug…-100n`, `t16-certain` kernel_2.json: 99 records at 0x150 and 99
     at 0x780, one per warp that passes `idx < N`.
   - Block 0 warp 1 of that launch: write 0x140 seq 499, syncwarp 0x150 seq 600, syncwarp 0x780
     seq 1209, read 0x790 seq 1301.
   - A warp that runs the helper also yields a record at the NOP: P3 `…Determ_NonPersist_Atomic…` has
     531 at 0x150, 531 at 0x730 and 1,062 at the helper's 0x10a0.
3. **HbClock and the oracle join there.** A `Syncwarp` record calls `sync_group` on its masked lanes
   (`pc_dependency_analysis.cpp:1661-1668`), which ticks the main and the barrier-only clock
   (`:1321-1338`); the oracle likewise (`hb_oracle.py:672-677`, `sync_group` `:313-333`). The X1 dumps
   agree:
   - no pending barrier instance in any launch;
   - vector-clock bases of at most 32 entries in all 570 P1 vector-clock launch-rows and in 152 of 166
     P3 ones;
   - 128 or 160 entries in the other 14 P3 launch-rows. Those kernels have RMWs, and an (ATOM) join
     is the one way a clock learns another warp's entries without a barrier (inference, not traced per
     launch).
4. **Every instance is ordered by one** (proved-in-effect over the 120 rows with records).
   - 13,013,400 conflicting instances, in 1,238 launch-records: every one same-warp, with a syncwarp
     record holding **both** lanes in its active mask between its two accesses.
   - 0 uncovered, 0 covered only through a sync mask, 0 cross-warp. Same-thread pairs (485,225) are
     no conflict.
   - Every u/v record is 1 byte (`size` 1).
5. **X1 agrees.**
   - In all 1,466 launch-records of the 128 rows the pair is in none of `hb_races`,
     `hb_races_sync_only`, `hb_sync_pass`.
   - The PCDG edge u -> v is present in every launch but one, in each of the 128 rows, with distance
     buckets intra-thread 186,114 and intra-warp 146,072, never block or grid.
   - The shared race X1 does list for each of these kernels is the set's lane/lane WAW, e.g.
     `(0x320, 0x320) WAW warp`: several lanes write `true` with no sync between them, a real data race.
     It is reported, `structural` (`confirm_final/…NonPersist_RaceBug…-default-100n__cuvein__vector-clock.json`:
     `shared:0x320-0x320:WAW`; the P3 programs `shared:0x340-0x340:WAW` and the like).
6. **The static side cannot see it.**
   - `sync_dominance.classify` returns a sync only for `BAR*` and `WARPSYNC`, and `None` for `NOP`
     (`python/sync_dominance.py:82-105`).
   - `HBGraph` builds `syncs` / `qualifying` from it (`:458`, `:476`), and the helper's `WARPSYNC` sits
     in another dot cluster that the kernel's graph does not enter.
   - X5's binner takes its barriers from `eng.qualifying`
     (`eval/baselines/setup/barrier_ordered_bins.py:156`), finds none, and returns `other` (`:188`). R1:
     strength `none` in all 128 rows.
7. **Counterfactual** (Appendix A).
   - Removing the cutting NOP's records makes the barrier-only clock list the pair (and the vector
     clock too) in 6–13 launches per row for 44 of the 64 pairs: all 80 of their rows that have
     records.
   - For the other 20 pairs it does not, and the barrier-only pairs at u or v stay just the lane/lane
     WAW. All 20 are in the 7 kernels where late lanes issue memory records inside a diverged-warp
     syncwarp instance (§4).
   - **RAW pairs (10):** the helper's own `WARPSYNC`, which every warp of those recordings executes
     (Appendices B, C), still orders the set before the read. That is correct, and it stays so after
     the merge of §4.
   - **WAW pairs (10):** what still orders them is a diverged-warp record (§4).

## 3. The cp.async pair

**SASS** (one block, `shared_writewrite_race.sm_89.dot`, md5 `9b2663413e6e`):

```
0060: LOP3.LUT R5, R0, 0x7c, RZ, 0xc0, !PT     ; R5 = (tid % 32) * 4
0070: LDGSTS.E [R5], [R2.64]                    ; u: cp.async global -> shared (async agent)
0080: LDGDEPBAR                                 ; pipeline_commit records
0090: DEPBAR.LE SB0, 0x0                        ; pipeline_wait records   (cp.async.wait_all, .cu:59)
00a0: BAR.SYNC.DEFER_BLOCKING 0x0               ; barrier records         (__syncthreads, .cu:60)
00b0: LDS R7, [R5]                              ; v
```

**Source** (`cuHadron/memcpy/shared_writewrite_race.cu:35-64`): 64 threads copy to
`shared_data[threadIdx.x % 32]`, so threads t and t+32 (different warps) write one word. The
labelled race is that copy/copy WAW.

**X1.**
- Both modes' confirm files: `RACE`, report id `shared:0x70-0x70:WAW`.
- `hb_races` (vector-clock): `(0x70, 0x70) WAW block, async 'ab'`, count 32.
- `hb_races_sync_only` / `hb_sync_pass`: `[112, 112, 32]`.
- (0x70, 0xb0) is in none of them; the PCDG edge 0x70 -> 0xb0 is intra-block 32.

**Records** (`t16-recorded-exits`, `hb_async: 1`): `pipeline_commit` 0x80 x2, `pipeline_wait` 0x90 x2,
`barrier` 0xa0 x2, `exit` 0xd0 x2. Every store of the program whose dump carries `hb_async` has the
same commit, wait and barrier records (exit records too, except `t1a-p56` and `t9-eval-*`), and each
lists only `(0x70, 0x70)` (`eval/x_logs/x5b-p6-stores-314619.log`).
- **64 instances** per mode, all cross-warp (t -> t+-32).
- **As recorded:** the oracle does not list the pair.
- **Removing any one of** the commit records, the wait records or the barrier records makes **both
  clocks** list it. So the copy is ordered for its issuer at the wait and reaches the other warp's
  reader through the barrier.

**Static side.**
- `HBGraph.ordered` alone gives R1 strength `block` (the barrier dominates).
- `judge` resets it to `none` because u is an async copy (`sync_dominance.py:1416-1426`, the T1a
  rule).
- So the class comes from the barrier-only clock (`_hb_class`, `:1190`).

**Verdict:** a correct ORDERED. The binner's detail already lists `0xa0 BAR.SYNC.DEFER_BLOCKING`. None
of X5's bins 1–4 fits a straight-line unconditional barrier, which is why it lands in `other`.

## 4. Syncwarp records of a diverged warp

**What the trace holds.** In 24 of the 60 (program, mode) recordings with records, the helper's
`WARPSYNC` is executed in **2 or 3 records** (active masks partial, `sync_mask` 0xffffffff):
`x5b_partial.py`, job 314625, Appendix C.
- Every instance completes: the union of the records' active masks reaches the mask.
- In 20 of the 24, the not-yet-arrived lanes issue **39,298 memory records** in total between the
  first record of an instance and its completion. The other 4 are the 1296-node Persist RaceBug
  programs: 0. These are accesses before their own arrival, which
  the per-record join treats as after it.
- Examples: P3 `…Determ_NonPersist_Atomic…-100n` 531 instances, 812 such records; Push
  `…NonPersist_RaceBug…-default-1296n` 9,480 / 9,239 instances (scalar / vector), 5,985 / 5,811
  records.

**What the code does with them.** `HbClock` joins every lane of `sync_mask` at each record:
`tids` from `a.accessSize` (`pc_dependency_analysis.cpp:1661-1668`); the oracle, every lane of
`e["sync_mask"]` (`hb_oracle.py:672-677`). The model reads a syncwarp record as a complete instance at
its own position (`hb_proof.tex:145`). The release condition is stated for barriers only (A3,
`:206-208`), and W2 is checked for barrier segments only (`:166-181`). For a diverged warp the
instance completes at the **first** group's record, not when the hardware releases.

**Effect on what is reported (tested, both clocks, 60 recordings).** Each completed partial instance
was merged into one record at its completion (active mask = the union; the earlier records dropped),
which is the exact instance under the model's own rule, and the trace was replayed as recorded and
merged. **0 race pc pairs appear and 0 disappear** in every recording, 0 replay errors. Replays were
full for the 100-node programs and shared-only for the 1296-node ones, so 1296-node global pairs are
not checked. Nothing that X1 or the confirm files report changes through this in these programs.

**Effect on a race the program could have (tested, job 314628).** For the 20 pairs of §2.2(7),
replaying with the cutting NOP's records removed:
- **as recorded**, no launch lists the pair;
- **after the merge**:
  - **WAW clear -> set (10 pairs, 20 rows):** listed by both clocks in 7–11 launches per row, e.g.
    P3 `…Determ_NonPersist_Atomic…` `(0x140, 0x340)` 7 of 11, Push `…NonPersist…` `(0x130, 0x320)`
    9–11 of 10–12;
  - **RAW set -> read (10 pairs, 20 rows):** still not listed, correctly, because the completed helper
    `WARPSYNC` orders the set before the read.

So in a program without the first `__syncwarp()`, the clear/set race is real, and the per-record join
of the diverged second `__syncwarp()` hides it. The early group's helper record orders lane 0's clear
before sets that lanes still in the loop make after it.

**Classification.**
- Not the mechanism of any of the 65 pairs: their instances are covered by syncwarp records with both
  lanes active, which is sound however the warp arrives.
- As a mechanism it is **(c) — a possible missed race.** It needs a diverged `WARPSYNC` whose early
  group precedes a conflicting pre-barrier access of a late lane, with nothing else ordering the pair.
- In these 60 recordings it changes nothing reported. **Corpus-wide: unmeasured.**

**What a fix would look like (a proposal, not made).** Treat syncwarp records like barrier arrivals:
accumulate active masks per (block, warp, pc) and join when they cover `sync_mask`. Add the matching
model change (the A3 analogue) and a TV check that no masked lane has a record between an instance's
first record and its completion (the W2 analogue).

## 5. The candidates in the brief

| candidate | result | evidence |
|---|---|---|
| location granularity — byte addresses vs word-aligned keys, in the harness or HbClock's bucket key | **ruled out** | HbClock: `Loc{space, block, addr}` with `addr = a.addresses[lane]`, the byte address (`pc_dependency_analysis.cpp:1756-1758`); its flat index is one-to-one on addresses — a 4-byte-aligned one in a 128-byte segment slot `(addr >> 2) & 31`, any other in an exact `(hi, addr)` table (`:433-460`). Oracle: `loc_of = (space, block, addr)` (`hb_oracle.py:452-454`). PCDG shared shadow: indexed by the byte offset (`object_entries[object_idx][addr]`, `pc_dependency_analysis.cpp:3268`; the dumps say `shadow_memory_granularity_bytes: 1`). The harness keys reports by pc pair, never by address |
| the two accesses touch disjoint bytes of one word | **ruled out** | u and v touch a common byte in 1,240 of the 1,360 launch-records with records (the other 120: one launch per row); (block, word) pairs shared only through different bytes: 0 in every row; every u/v record is 1 byte; the address is the warp index |
| the CFG binner misses a barrier through an inlined or predicated path | **not a path effect** | the missed sync is the unpredicated `NOP` the Sanitizer reports as a syncwarp, on every u -> v path (§2.2). Related: in 12 kernels a `__syncwarp()` also has a `CALL`ed helper `WARPSYNC`, in a separate dot cluster the kernel graph does not enter; the NOP stays on every u -> v path |
| a real ordering the binner's rule does not see | **yes — the mechanism** | the binner (and R1) count `BAR`/`WARPSYNC` opcodes; the ordering is the syncwarp the Sanitizer reports at the NOP (§2) |

## 6. What this means for X5 and X3

* **X5 Tables 1 and 5.**
  - With the NOPs read as `WARPSYNC 0xffffffff`, X5's binner puts all 64 pairs (128 rows) in
    `partial participation` (bin 2: a WARPSYNC between). `other` would hold the P6 pair alone.
  - X5 §2.2's "none has a qualifying barrier on any CFG path between u and v" and "no BAR or WARPSYNC
    anywhere in the kernel" hold for the printed SASS only.
  - Its candidate "a word-granular edge against a byte-exact conflict check" is refuted (§5).
* **R1.**
  - Strength `none` for all 64 pairs. With the NOP read as WARPSYNC: `warp` for the 32 NonPersist
    pairs, still `none` for the 32 Persist pairs (the syncwarps inside the grid-stride loop).
  - The static leg hands these pairs to the barrier-only clock, which orders them: an under-ordering,
    not a soundness issue (CLAUDE.md A4: ORDERED from the barrier-only clock is a sanctioned source).
* **X3.**
  - The 65 `barrier-ordered` verdicts are correct ORDERED verdicts, and the 64 byte pairs' order does
    not depend on §4.
  - §4 is the item that touches X3's soundness claims. A diverged `WARPSYNC` is joined per record, the
    trusted base does not state its release condition, and a constructed counterfactual shows it
    hiding real races. In the recordings measured it hides nothing.
  - **Not measured:** how often diverged syncwarps occur corpus-wide and whether any reported verdict
    depends on them. That needs the census of §4 over a store with `hb_events` per program.
  - Also not measured: how many other kernels have syncwarps printed as NOP, which would move pairs
    between R1 `ordered` and `barrier-ordered` and between X5's bins, not between RACE and ORDERED.

## 7. Files and jobs

Scripts (`eval/baselines/setup/`):

| file | what it does |
|---|---|
| `x5b_byte_pairs.py` | per-row static / X1 / records / counterfactual facts (`--shared-only`, `--shard`, `--rows`) |
| `x5b_merge.py`, `x5b_summary.py`, `x5b_tables.py` | merge the shared-only and full replays and compare them; the mechanism rule and tables; the appendices of this report |
| `x5b_partial.py` | diverged-warp syncwarp census, the strict instance check, the merged replay (§4) |
| `x5b_cf_merged.py` | the counterfactual on merged traces (§4) |
| `x5b_events.py`, `x5b_syncpcs.py`, `x5b_calls.py`, `x5b_p6_stores.py`, `x5b_sources.sh`, `x5b_probe_{dots,p6,clusters}.sh` | record printer, sync records per pc with the dot's opcode, CALL sites and the warpsync helper, the P6 program in every store, the 14 sources, dot md5s across stores |
| `p_x5b_{run,split45,shared,report,partial,cfm}.sh` | the sbatch wrappers |

Outputs (`eval/results/x5b/`):

| file | contents |
|---|---|
| `byte_pairs.jsonl` | merged per-row records: shared-only, with `events_full` where a full replay exists |
| `byte_pairs_so_*.jsonl` | the shared-only shards |
| `byte_pairs_shard*.jsonl`, `byte_pairs_sub*.jsonl` | the full replays that finished |
| `shared_only_check.md`, `byte_pairs_tables.md` | the comparison; the mechanism and per-row tables |
| `partial*.jsonl`, `cf_merged*.jsonl` | §4 |
| `report_tables.md` | the appendices below |

Logs: `eval/x_logs/x5b-*.log` (force-added; `*.log` is gitignored).

Jobs, all partition `normal`:

| job | what it was | outcome |
|---|---|---|
| 314473 | first full run | cancelled after 2 rows, too slow |
| 314474 | 8 shards, full replay | shards 4–5 cancelled and split |
| 314529 | 16 pieces | 8 pieces OOM-killed; their rows went shared-only |
| 314546 | the 14 sources | — |
| 314582, 314584, 314590, 314591 | — | cancelled before start, replaced by 314619 |
| 314619 | shared-only, all rows, 16 processes on one node, with the P6 survey as step `.0` | — |
| 314621 | merge, summary | — |
| 314622 | sync pcs | — |
| 314623 | dot clusters | — |
| 314624 | CALL sites | — |
| 314625 | diverged-warp check | — |
| 314626, 314627 | tables | — |
| 314628 | merged counterfactual | — |
| 314629 | probes re-run | — |

Python `/home/fzheng4/AccelProf/.env/bin/python`, `CUVEIN_HOME` = this worktree.

## Appendix (generated: `eval/results/x5b/report_tables.md`)

Program names drop `CC_CUDA_V_Data_`, `_IntType`, `_Warp`, `_ReadWrite`, `_NonDup` and every
`_No…Bug`. Paired cells are vector-clock / scalar-clock. "no store" = no recording with records (the 8
vector-clock rows of §0.3).

### A. Per program and pair (vector-clock / scalar-clock)

| suite | program | u -> v | type | opcodes | NOP on every path (syncwarp pc) | X1 launches with edge u->v | X1 lists the pair | syncwarp records at that pc | instances: syncwarp between (both lanes active) / not | oracle as recorded lists it | that pc's records removed: lists it (launches) | R1 / with NOP as WARPSYNC |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P1 | P1-Pull_Determ_NonPersist_RaceBug-default-100n | 0x140 -> 0x320 | WAW | STS.U8 / STS.U8 | 0x150 | 10/11 / 10/11 | 0 / 0 | syncwarp 760 / syncwarp 760 | 632 / 0 / 632 / 0 | 0/11 / 0/11 | 0x150: 9 / 0x150: 9 | none / warp |
| P1 | P1-Pull_Determ_NonPersist_RaceBug-default-100n | 0x320 -> 0x790 | RAW | STS.U8 / LDS.U8 | 0x780 | 10/11 / 10/11 | 0 / 0 | syncwarp 760 / syncwarp 760 | 27032 / 0 / 27032 / 0 | 0/11 / 0/11 | 0x780: 10 / 0x780: 10 | none / warp |
| P1 | P1-Pull_Determ_NonPersist_RaceBug-default-1296n | 0x140 -> 0x320 | WAW | STS.U8 / STS.U8 | 0x150 | 13/14 / 12/13 | 0 / 0 | syncwarp 11971 / syncwarp 12194 | 27319 / 0 / 27764 / 0 | 0/14 / 0/13 | 0x150: 9 / 0x150: 9 | none / warp |
| P1 | P1-Pull_Determ_NonPersist_RaceBug-default-1296n | 0x320 -> 0x790 | RAW | STS.U8 / LDS.U8 | 0x780 | 13/14 / 12/13 | 0 / 0 | syncwarp 11971 / syncwarp 12194 | 994945 / 0 / 1010166 / 0 | 0/14 / 0/13 | 0x780: 13 / 0x780: 12 | none / warp |
| P1 | P1-Pull_Determ_NonPersist_RaceBug-slower_atomic-100n | 0x140 -> 0x320 | WAW | STS.U8 / STS.U8 | 0x150 | 10/11 / 10/11 | 0 / 0 | syncwarp 761 / syncwarp 763 | 633 / 0 / 640 / 0 | 0/11 / 0/12 | 0x150: 9 / 0x150: 9 | none / warp |
| P1 | P1-Pull_Determ_NonPersist_RaceBug-slower_atomic-100n | 0x320 -> 0x790 | RAW | STS.U8 / LDS.U8 | 0x780 | 10/11 / 10/11 | 0 / 0 | syncwarp 761 / syncwarp 763 | 27094 / 0 / 27373 / 0 | 0/11 / 0/12 | 0x780: 10 / 0x780: 11 | none / warp |
| P1 | P1-Pull_Determ_NonPersist_RaceBug-slower_atomic-1296n | 0x140 -> 0x320 | WAW | STS.U8 / STS.U8 | 0x150 | 13/14 / 13/14 | 0 / 0 | syncwarp 12205 / syncwarp 11852 | 27686 / 0 / 27152 / 0 | 0/14 / 0/13 | 0x150: 10 / 0x150: 9 | none / warp |
| P1 | P1-Pull_Determ_NonPersist_RaceBug-slower_atomic-1296n | 0x320 -> 0x790 | RAW | STS.U8 / LDS.U8 | 0x780 | 13/14 / 13/14 | 0 / 0 | syncwarp 12205 / syncwarp 11852 | 1008089 / 0 / 988528 / 0 | 0/14 / 0/13 | 0x780: 13 / 0x780: 12 | none / warp |
| P1 | P1-Pull_Determ_Persist_RaceBug-default-100n | 0x130 -> 0x380 | WAW | STS.U8 / STS.U8 | 0x200 | 10/11 / 10/11 | 0 / 0 | syncwarp 775 / syncwarp 774 | 633 / 0 / 638 / 0 | 0/11 / 0/11 | 0x200: 9 / 0x200: 9 | none / none |
| P1 | P1-Pull_Determ_Persist_RaceBug-default-100n | 0x380 -> 0xa30 | RAW | STS.U8 / LDS.U8 | 0xa20 | 10/11 / 10/11 | 0 / 0 | syncwarp 775 / syncwarp 774 | 27063 / 0 / 27404 / 0 | 0/11 / 0/11 | 0xa20: 10 / 0xa20: 10 | none / none |
| P1 | P1-Pull_Determ_Persist_RaceBug-default-1296n | 0x130 -> 0x380 | WAW | STS.U8 / STS.U8 | 0x200 | 13/14 / 12/13 | 0 / 0 | no store / syncwarp 12131 | no store / 27644 / 0 | no store / 0/14 | no store / 0x200: 10 | none / none |
| P1 | P1-Pull_Determ_Persist_RaceBug-default-1296n | 0x380 -> 0xa30 | RAW | STS.U8 / LDS.U8 | 0xa20 | 13/14 / 12/13 | 0 / 0 | no store / syncwarp 12131 | no store / 1007717 / 0 | no store / 0/14 | no store / 0xa20: 13 | none / none |
| P1 | P1-Pull_Determ_Persist_RaceBug-slower_atomic-100n | 0x130 -> 0x380 | WAW | STS.U8 / STS.U8 | 0x200 | 10/11 / 10/11 | 0 / 0 | syncwarp 794 / syncwarp 795 | 639 / 0 / 649 / 0 | 0/11 / 0/11 | 0x200: 9 / 0x200: 9 | none / none |
| P1 | P1-Pull_Determ_Persist_RaceBug-slower_atomic-100n | 0x380 -> 0xa30 | RAW | STS.U8 / LDS.U8 | 0xa20 | 10/11 / 10/11 | 0 / 0 | syncwarp 794 / syncwarp 795 | 27435 / 0 / 27745 / 0 | 0/11 / 0/11 | 0xa20: 10 / 0xa20: 10 | none / none |
| P1 | P1-Pull_Determ_Persist_RaceBug-slower_atomic-1296n | 0x130 -> 0x380 | WAW | STS.U8 / STS.U8 | 0x200 | 13/14 / 13/14 | 0 / 0 | no store / syncwarp 12085 | no store / 27534 / 0 | no store / 0/14 | no store / 0x200: 10 | none / none |
| P1 | P1-Pull_Determ_Persist_RaceBug-slower_atomic-1296n | 0x380 -> 0xa30 | RAW | STS.U8 / LDS.U8 | 0xa20 | 13/14 / 13/14 | 0 / 0 | no store / syncwarp 12085 | no store / 1002788 / 0 | no store / 0/14 | no store / 0xa20: 13 | none / none |
| P1 | P1-Pull_NonDeterm_NonPersist_RaceBug-default-100n | 0x130 -> 0x2f0 | WAW | STS.U8 / STS.U8 | 0x140 | 10/11 / 10/11 | 0 / 0 | syncwarp 760 / syncwarp 760 | 633 / 0 / 633 / 0 | 0/11 / 0/11 | 0x140: 9 / 0x140: 9 | none / warp |
| P1 | P1-Pull_NonDeterm_NonPersist_RaceBug-default-100n | 0x2f0 -> 0x1130 | RAW | STS.U8 / LDS.U8 | 0x1120 | 10/11 / 10/11 | 0 / 0 | syncwarp 760 / syncwarp 760 | 27032 / 0 / 27032 / 0 | 0/11 / 0/11 | 0x1120: 10 / 0x1120: 10 | none / warp |
| P1 | P1-Pull_NonDeterm_NonPersist_RaceBug-default-1296n | 0x130 -> 0x2f0 | WAW | STS.U8 / STS.U8 | 0x140 | 13/14 / 11/12 | 0 / 0 | syncwarp 11820 / syncwarp 11498 | 26486 / 0 / 25802 / 0 | 0/13 / 0/13 | 0x140: 9 / 0x140: 11 | none / warp |
| P1 | P1-Pull_NonDeterm_NonPersist_RaceBug-default-1296n | 0x2f0 -> 0x1130 | RAW | STS.U8 / LDS.U8 | 0x1120 | 13/14 / 11/12 | 0 / 0 | syncwarp 11820 / syncwarp 11498 | 961651 / 0 / 937409 / 0 | 0/13 / 0/13 | 0x1120: 12 / 0x1120: 12 | none / warp |
| P1 | P1-Pull_NonDeterm_NonPersist_RaceBug-slower_atomic-100n | 0x130 -> 0x2f0 | WAW | STS.U8 / STS.U8 | 0x140 | 10/11 / 10/11 | 0 / 0 | syncwarp 760 / syncwarp 760 | 633 / 0 / 633 / 0 | 0/11 / 0/11 | 0x140: 9 / 0x140: 9 | none / warp |
| P1 | P1-Pull_NonDeterm_NonPersist_RaceBug-slower_atomic-100n | 0x2f0 -> 0x1130 | RAW | STS.U8 / LDS.U8 | 0x1120 | 10/11 / 10/11 | 0 / 0 | syncwarp 760 / syncwarp 760 | 27032 / 0 / 27032 / 0 | 0/11 / 0/11 | 0x1120: 10 / 0x1120: 10 | none / warp |
| P1 | P1-Pull_NonDeterm_NonPersist_RaceBug-slower_atomic-1296n | 0x130 -> 0x2f0 | WAW | STS.U8 / STS.U8 | 0x140 | 11/12 / 11/12 | 0 / 0 | syncwarp 10932 / syncwarp 11304 | 25035 / 0 / 25443 / 0 | 0/11 / 0/12 | 0x140: 9 / 0x140: 9 | none / warp |
| P1 | P1-Pull_NonDeterm_NonPersist_RaceBug-slower_atomic-1296n | 0x2f0 -> 0x1130 | RAW | STS.U8 / LDS.U8 | 0x1120 | 11/12 / 11/12 | 0 / 0 | syncwarp 10932 / syncwarp 11304 | 908393 / 0 / 921971 / 0 | 0/11 / 0/12 | 0x1120: 10 / 0x1120: 11 | none / warp |
| P1 | P1-Pull_NonDeterm_Persist_RaceBug-default-100n | 0x130 -> 0x330 | WAW | STS.U8 / STS.U8 | 0x1f0 | 9/10 / 10/11 | 0 / 0 | syncwarp 723 / syncwarp 673 | 619 / 0 / 614 / 0 | 0/10 / 0/10 | 0x1f0: 8 / 0x1f0: 9 | none / none |
| P1 | P1-Pull_NonDeterm_Persist_RaceBug-default-100n | 0x330 -> 0x1330 | RAW | STS.U8 / LDS.U8 | 0x1320 | 9/10 / 10/11 | 0 / 0 | syncwarp 723 / syncwarp 673 | 26412 / 0 / 26350 / 0 | 0/10 / 0/10 | 0x1320: 9 / 0x1320: 9 | none / none |
| P1 | P1-Pull_NonDeterm_Persist_RaceBug-default-1296n | 0x130 -> 0x330 | WAW | STS.U8 / STS.U8 | 0x1f0 | 12/13 / 12/13 | 0 / 0 | no store / syncwarp 11486 | no store / 25870 / 0 | no store / 0/13 | no store / 0x1f0: 10 | none / none |
| P1 | P1-Pull_NonDeterm_Persist_RaceBug-default-1296n | 0x330 -> 0x1330 | RAW | STS.U8 / LDS.U8 | 0x1320 | 12/13 / 12/13 | 0 / 0 | no store / syncwarp 11486 | no store / 940013 / 0 | no store / 0/13 | no store / 0x1320: 12 | none / none |
| P1 | P1-Pull_NonDeterm_Persist_RaceBug-slower_atomic-100n | 0x130 -> 0x330 | WAW | STS.U8 / STS.U8 | 0x1f0 | 9/10 / 8/9 | 0 / 0 | syncwarp 741 / syncwarp 636 | 680 / 0 / 565 / 0 | 0/10 / 0/9 | 0x1f0: 8 / 0x1f0: 8 | none / none |
| P1 | P1-Pull_NonDeterm_Persist_RaceBug-slower_atomic-100n | 0x330 -> 0x1330 | RAW | STS.U8 / LDS.U8 | 0x1320 | 9/10 / 8/9 | 0 / 0 | syncwarp 741 / syncwarp 636 | 28210 / 0 / 24056 / 0 | 0/10 / 0/9 | 0x1320: 9 / 0x1320: 8 | none / none |
| P1 | P1-Pull_NonDeterm_Persist_RaceBug-slower_atomic-1296n | 0x130 -> 0x330 | WAW | STS.U8 / STS.U8 | 0x1f0 | 12/13 / 13/14 | 0 / 0 | no store / syncwarp 11452 | no store / 25852 / 0 | no store / 0/13 | no store / 0x1f0: 10 | none / none |
| P1 | P1-Pull_NonDeterm_Persist_RaceBug-slower_atomic-1296n | 0x330 -> 0x1330 | RAW | STS.U8 / LDS.U8 | 0x1320 | 12/13 / 13/14 | 0 / 0 | no store / syncwarp 11452 | no store / 940757 / 0 | no store / 0/13 | no store / 0x1320: 12 | none / none |
| P1 | P1-Push_NonDeterm_NonPersist_RaceBug-default-100n | 0x130 -> 0x320 | WAW | STS.U8 / STS.U8 | 0x140 | 11/12 / 11/12 | 0 / 0 | syncwarp 686 / syncwarp 744 | 656 / 0 / 693 / 0 | 0/11 / 0/12 | 0x140: 0 / 0x140: 0 | none / warp |
| P1 | P1-Push_NonDeterm_NonPersist_RaceBug-default-100n | 0x320 -> 0xe70 | RAW | STS.U8 / LDS.U8 | 0xe50 | 11/12 / 11/12 | 0 / 0 | syncwarp 686 / syncwarp 744 | 656 / 0 / 693 / 0 | 0/11 / 0/12 | 0xe50: 0 / 0xe50: 0 | none / warp |
| P1 | P1-Push_NonDeterm_NonPersist_RaceBug-default-1296n | 0x130 -> 0x320 | WAW | STS.U8 / STS.U8 | 0x140 | 9/10 / 9/10 | 0 / 0 | syncwarp 9239 / syncwarp 9480 | 17239 / 0 / 17850 / 0 | 0/10 / 0/11 | 0x140: 0 / 0x140: 0 | none / warp |
| P1 | P1-Push_NonDeterm_NonPersist_RaceBug-default-1296n | 0x320 -> 0xe70 | RAW | STS.U8 / LDS.U8 | 0xe50 | 9/10 / 9/10 | 0 / 0 | syncwarp 9239 / syncwarp 9480 | 17239 / 0 / 17850 / 0 | 0/10 / 0/11 | 0xe50: 0 / 0xe50: 0 | none / warp |
| P1 | P1-Push_NonDeterm_NonPersist_RaceBug-slower_atomic-100n | 0x130 -> 0x320 | WAW | STS.U8 / STS.U8 | 0x140 | 10/11 / 10/11 | 0 / 0 | syncwarp 740 / syncwarp 714 | 742 / 0 / 681 / 0 | 0/12 / 0/12 | 0x140: 0 / 0x140: 0 | none / warp |
| P1 | P1-Push_NonDeterm_NonPersist_RaceBug-slower_atomic-100n | 0x320 -> 0xe70 | RAW | STS.U8 / LDS.U8 | 0xe50 | 10/11 / 10/11 | 0 / 0 | syncwarp 740 / syncwarp 714 | 742 / 0 / 681 / 0 | 0/12 / 0/12 | 0xe50: 0 / 0xe50: 0 | none / warp |
| P1 | P1-Push_NonDeterm_NonPersist_RaceBug-slower_atomic-1296n | 0x130 -> 0x320 | WAW | STS.U8 / STS.U8 | 0x140 | 11/12 / 9/10 | 0 / 0 | syncwarp 9266 / syncwarp 9570 | 17483 / 0 / 17790 / 0 | 0/10 / 0/11 | 0x140: 0 / 0x140: 0 | none / warp |
| P1 | P1-Push_NonDeterm_NonPersist_RaceBug-slower_atomic-1296n | 0x320 -> 0xe70 | RAW | STS.U8 / LDS.U8 | 0xe50 | 11/12 / 9/10 | 0 / 0 | syncwarp 9266 / syncwarp 9570 | 17483 / 0 / 17790 / 0 | 0/10 / 0/11 | 0xe50: 0 / 0xe50: 0 | none / warp |
| P1 | P1-Push_NonDeterm_Persist_RaceBug-default-100n | 0x100 -> 0x3a0 | WAW | STS.U8 / STS.U8 | 0x1f0 | 10/11 / 10/11 | 0 / 0 | syncwarp 695 / syncwarp 641 | 565 / 0 / 519 / 0 | 0/12 / 0/11 | 0x1f0: 11 / 0x1f0: 10 | none / none |
| P1 | P1-Push_NonDeterm_Persist_RaceBug-default-100n | 0x3a0 -> 0x13a0 | RAW | STS.U8 / LDS.U8 | 0x1370 | 10/11 / 10/11 | 0 / 0 | syncwarp 695 / syncwarp 641 | 565 / 0 / 519 / 0 | 0/12 / 0/11 | 0x1370: 11 / 0x1370: 10 | none / none |
| P1 | P1-Push_NonDeterm_Persist_RaceBug-default-1296n | 0x100 -> 0x3a0 | WAW | STS.U8 / STS.U8 | 0x1f0 | 11/12 / 11/12 | 0 / 0 | syncwarp 9072 / syncwarp 9046 | 13894 / 0 / 14263 / 0 | 0/12 / 0/11 | 0x1f0: 11 / 0x1f0: 10 | none / none |
| P1 | P1-Push_NonDeterm_Persist_RaceBug-default-1296n | 0x3a0 -> 0x13a0 | RAW | STS.U8 / LDS.U8 | 0x1370 | 11/12 / 11/12 | 0 / 0 | syncwarp 9072 / syncwarp 9046 | 13894 / 0 / 14263 / 0 | 0/12 / 0/11 | 0x1370: 11 / 0x1370: 10 | none / none |
| P1 | P1-Push_NonDeterm_Persist_RaceBug-slower_atomic-100n | 0x100 -> 0x3a0 | WAW | STS.U8 / STS.U8 | 0x1f0 | 10/11 / 10/11 | 0 / 0 | syncwarp 677 / syncwarp 693 | 558 / 0 / 576 / 0 | 0/11 / 0/12 | 0x1f0: 10 / 0x1f0: 11 | none / none |
| P1 | P1-Push_NonDeterm_Persist_RaceBug-slower_atomic-100n | 0x3a0 -> 0x13a0 | RAW | STS.U8 / LDS.U8 | 0x1370 | 10/11 / 10/11 | 0 / 0 | syncwarp 677 / syncwarp 693 | 558 / 0 / 576 / 0 | 0/11 / 0/12 | 0x1370: 10 / 0x1370: 11 | none / none |
| P1 | P1-Push_NonDeterm_Persist_RaceBug-slower_atomic-1296n | 0x100 -> 0x3a0 | WAW | STS.U8 / STS.U8 | 0x1f0 | 11/12 / 11/12 | 0 / 0 | syncwarp 9130 / syncwarp 9187 | 14454 / 0 / 14107 / 0 | 0/12 / 0/12 | 0x1f0: 11 / 0x1f0: 11 | none / none |
| P1 | P1-Push_NonDeterm_Persist_RaceBug-slower_atomic-1296n | 0x3a0 -> 0x13a0 | RAW | STS.U8 / LDS.U8 | 0x1370 | 11/12 / 11/12 | 0 / 0 | syncwarp 9130 / syncwarp 9187 | 14454 / 0 / 14107 / 0 | 0/12 / 0/12 | 0x1370: 11 / 0x1370: 11 | none / none |
| P3 | P3-Pull_Determ_NonPersist_Atomic-100n | 0x140 -> 0x340 | WAW | STS.U8 / STS.U8 | 0x150 | 10/11 / 10/11 | 0 / 0 | syncwarp 531 / syncwarp 531 | 526 / 0 / 526 / 0 | 0/11 / 0/11 | 0x150: 0 / 0x150: 0 | none / warp |
| P3 | P3-Pull_Determ_NonPersist_Atomic-100n | 0x340 -> 0x740 | RAW | STS.U8 / LDS.U8 | 0x730 | 10/11 / 10/11 | 0 / 0 | syncwarp 531 / syncwarp 531 | 22816 / 0 / 22816 / 0 | 0/11 / 0/11 | 0x730: 0 / 0x730: 0 | none / warp |
| P3 | P3-Pull_Determ_NonPersist_CudaAtomic-100n | 0x180 -> 0x380 | WAW | STS.U8 / STS.U8 | 0x190 | 10/11 / 10/11 | 0 / 0 | syncwarp 531 / syncwarp 531 | 526 / 0 / 526 / 0 | 0/11 / 0/11 | 0x190: 0 / 0x190: 0 | none / warp |
| P3 | P3-Pull_Determ_NonPersist_CudaAtomic-100n | 0x380 -> 0xc50 | RAW | STS.U8 / LDS.U8 | 0xc40 | 10/11 / 10/11 | 0 / 0 | syncwarp 531 / syncwarp 531 | 22816 / 0 / 22816 / 0 | 0/11 / 0/11 | 0xc40: 0 / 0xc40: 0 | none / warp |
| P3 | P3-Pull_Determ_Persist_Atomic-100n | 0x130 -> 0x380 | WAW | STS.U8 / STS.U8 | 0x200 | 10/11 / 10/11 | 0 / 0 | syncwarp 531 / syncwarp 531 | 526 / 0 / 526 / 0 | 0/11 / 0/11 | 0x200: 7 / 0x200: 7 | none / none |
| P3 | P3-Pull_Determ_Persist_Atomic-100n | 0x380 -> 0x980 | RAW | STS.U8 / LDS.U8 | 0x970 | 10/11 / 10/11 | 0 / 0 | syncwarp 531 / syncwarp 531 | 22816 / 0 / 22816 / 0 | 0/11 / 0/11 | 0x970: 10 / 0x970: 10 | none / none |
| P3 | P3-Pull_Determ_Persist_CudaAtomic-100n | 0x1f0 -> 0x450 | WAW | STS.U8 / STS.U8 | 0x250 | 10/11 / 10/11 | 0 / 0 | syncwarp 531 / syncwarp 531 | 526 / 0 / 526 / 0 | 0/11 / 0/11 | 0x250: 0 / 0x250: 0 | none / none |
| P3 | P3-Pull_Determ_Persist_CudaAtomic-100n | 0x450 -> 0x1150 | RAW | STS.U8 / LDS.U8 | 0x1140 | 10/11 / 10/11 | 0 / 0 | syncwarp 531 / syncwarp 531 | 22816 / 0 / 22816 / 0 | 0/11 / 0/11 | 0x1140: 0 / 0x1140: 0 | none / none |
| P3 | P3-Pull_NonDeterm_NonPersist_Atomic-100n | 0x140 -> 0x2e0 | WAW | STS.U8 / STS.U8 | 0x150 | 10/11 / 10/11 | 0 / 0 | syncwarp 531 / syncwarp 531 | 526 / 0 / 526 / 0 | 0/11 / 0/11 | 0x150: 0 / 0x150: 0 | none / warp |
| P3 | P3-Pull_NonDeterm_NonPersist_Atomic-100n | 0x2e0 -> 0x10b0 | RAW | STS.U8 / LDS.U8 | 0x10a0 | 10/11 / 10/11 | 0 / 0 | syncwarp 531 / syncwarp 531 | 22816 / 0 / 22816 / 0 | 0/11 / 0/11 | 0x10a0: 0 / 0x10a0: 0 | none / warp |
| P3 | P3-Pull_NonDeterm_NonPersist_CudaAtomic-100n | 0x170 -> 0x340 | WAW | STS.U8 / STS.U8 | 0x180 | 10/11 / 10/11 | 0 / 0 | syncwarp 531 / syncwarp 531 | 526 / 0 / 526 / 0 | 0/11 / 0/11 | 0x180: 0 / 0x180: 0 | none / warp |
| P3 | P3-Pull_NonDeterm_NonPersist_CudaAtomic-100n | 0x340 -> 0x8d0 | RAW | STS.U8 / LDS.U8 | 0x8c0 | 10/11 / 10/11 | 0 / 0 | syncwarp 531 / syncwarp 531 | 22816 / 0 / 22816 / 0 | 0/11 / 0/11 | 0x8c0: 0 / 0x8c0: 0 | none / warp |
| P3 | P3-Pull_NonDeterm_Persist_Atomic-100n | 0x1a0 -> 0x340 | WAW | STS.U8 / STS.U8 | 0x200 | 7/8 / 8/9 | 0 / 0 | syncwarp 534 / syncwarp 537 | 461 / 0 / 484 / 0 | 0/9 / 0/9 | 0x200: 6 / 0x200: 7 | none / none |
| P3 | P3-Pull_NonDeterm_Persist_Atomic-100n | 0x340 -> 0x1280 | RAW | STS.U8 / LDS.U8 | 0x1270 | 7/8 / 8/9 | 0 / 0 | syncwarp 534 / syncwarp 537 | 19778 / 0 / 20646 / 0 | 0/9 / 0/9 | 0x1270: 8 / 0x1270: 8 | none / none |
| P3 | P3-Pull_NonDeterm_Persist_CudaAtomic-100n | 0x1e0 -> 0x420 | WAW | STS.U8 / STS.U8 | 0x240 | 8/9 / 9/10 | 0 / 0 | syncwarp 582 / syncwarp 586 | 491 / 0 / 504 / 0 | 0/9 / 0/10 | 0x240: 0 / 0x240: 0 | none / none |
| P3 | P3-Pull_NonDeterm_Persist_CudaAtomic-100n | 0x420 -> 0xcc0 | RAW | STS.U8 / LDS.U8 | 0xcb0 | 8/9 / 9/10 | 0 / 0 | syncwarp 582 / syncwarp 586 | 21328 / 0 / 22010 / 0 | 0/9 / 0/10 | 0xcb0: 0 / 0xcb0: 0 | none / none |
| P6 | P6-memcpy-shared_writewrite_race-racy | 0x70 -> 0xb0 | RAW | LDGSTS.E / LDS | 0x80 LDGDEPBAR, 0x90 DEPBAR.LE, 0xa0 BAR.SYNC.DEFER_BLOCKING | 1/1 / 1/1 | 0 / 0 | pipeline_commit 2; pipeline_wait 2; barrier 2 / pipeline_commit 2; pipeline_wait 2; barrier 2 | cross-warp 64 / cross-warp 64 | 0/1 / 0/1 | 0x80+0x90+0xa0: 1; 0x80: 1; 0x90: 1; 0xa0: 1 / 0x80+0x90+0xa0: 1; 0x80: 1; 0x90: 1; 0xa0: 1 | block / — |

### B. Per kernel: syncwarp instructions and records

- `CC_CUDA_V_Data_Pull_Determ_IntType_NonPersist_RaceBug_Warp_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug` (4 programs): NOPs 0150, 0780; CALL none; helper `none`; syncwarp records (all its recordings in the events store, both modes): full 0x150 51266, full 0x780 51266
- `CC_CUDA_V_Data_Pull_Determ_IntType_Persist_RaceBug_Warp_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug` (4 programs): NOPs 0200, 0a20, 1700; CALL 01e0 -> returns to 01f0 (IMAD.IADD), 0a10 -> returns to 0a20 (NOP), 16a0 -> returns to 16b0 (BRA), 16f0 -> returns to 1700 (NOP); helper `IMAD.MOV.U32 R9, RZ, RZ, 0x0 ; | WARPSYNC R19 ; | RET.REL.NODEC R8 `(_Z14cc_vertex_data8ECLgraphPiS0_PKiiS0_S0_iS0_) ;`; syncwarp records (all its recordings in the events store, both modes): full 0x200 27354, full 0xa20 27354, full 0x1700 117504, partial 0x1730 27642
- `CC_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_RaceBug_Warp_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug` (4 programs): NOPs 0140, 1120; CALL none; helper `none`; syncwarp records (all its recordings in the events store, both modes): full 0x140 48594, full 0x1120 48594
- `CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_RaceBug_Warp_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug` (4 programs): NOPs 01f0, 1320, 1fe0; CALL 01d0 -> returns to 01e0 (IMAD.IADD), 1310 -> returns to 1320 (NOP), 1f80 -> returns to 1f90 (BRA), 1fd0 -> returns to 1fe0 (NOP); helper `IMAD.MOV.U32 R11, RZ, RZ, 0x0 ; | WARPSYNC R0 ; | RET.REL.NODEC R10 `(_Z14cc_vertex_data8ECLgraphPiPKiiS0_S0_iS0_) ;`; syncwarp records (all its recordings in the events store, both modes): full 0x1f0 25711, full 0x1320 25711, full 0x1fe0 106080, partial 0x2010 26312
- `CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_NonPersist_RaceBug_Warp_NonDup_NoNbrBoundsBug_NoExcessThreadsBug_NoLivelockBug_NoFieldBug` (4 programs): NOPs 0140, 0e50; CALL 0e40 -> returns to 0e50 (NOP); helper `IMAD.MOV.U32 R3, RZ, RZ, 0x0 ; | WARPSYNC 0xffffffff ; | RET.REL.NODEC R2 `(_Z14cc_vertex_data8ECLgraphPiPKiiS0_S0_iS0_) ;`; syncwarp records (all its recordings in the events store, both modes): full 0x140 40439, full 0xe50 40439, partial 0x1010 80878
- `CC_CUDA_V_Data_Push_NonDeterm_IntType_ReadWrite_Persist_RaceBug_Warp_NonDup_NoNbrBoundsBug_NoBoundsBug_NoLivelockBug_NoFieldBug` (4 programs): NOPs 01f0, 1370, 1570; CALL 01d0 -> returns to 01e0 (IMAD.IADD), 1360 -> returns to 1370 (NOP), 1560 -> returns to 1570 (NOP), 1580 -> returns to 1590 (BRA); helper `IMAD.MOV.U32 R3, RZ, RZ, 0x0 ; | WARPSYNC R9 ; | RET.REL.NODEC R2 `(_Z14cc_vertex_data8ECLgraphPiPKiiS0_S0_iS0_) ;`; syncwarp records (all its recordings in the events store, both modes): full 0x1f0 39141, full 0x1370 39141, full 0x1570 39141
- `CC_CUDA_V_Data_Pull_Determ_IntType_NonPersist_Atomic_Warp_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug` (1 programs): NOPs 0150, 0730; CALL 0720 -> returns to 0730 (NOP); helper `IMAD.MOV.U32 R9, RZ, RZ, 0x0 ; | WARPSYNC 0xffffffff ; | RET.REL.NODEC R8 `(_Z14cc_vertex_data8ECLgraphPiS0_PKiiS0_S0_iS0_) ;`; syncwarp records (all its recordings in the events store, both modes): full 0x150 1062, full 0x730 1062, partial 0x10a0 2124
- `CC_CUDA_V_Data_Pull_Determ_IntType_NonPersist_CudaAtomic_Warp_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug` (1 programs): NOPs 0190, 0c40; CALL 0c30 -> returns to 0c40 (NOP); helper `IMAD.MOV.U32 R9, RZ, RZ, 0x0 ; | WARPSYNC 0xffffffff ; | RET.REL.NODEC R8 `(_Z14cc_vertex_data8ECLgraphPN4cuda3__46atomicIiLNS0_3std3__412thread_scopeE0EEES7_PKiiPiSA_iSA_) ;`; syncwarp records (all its recordings in the events store, both modes): full 0x190 1062, full 0xc40 1062, partial 0x1600 2548
- `CC_CUDA_V_Data_Pull_Determ_IntType_Persist_Atomic_Warp_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug` (1 programs): NOPs 0200, 0970, 1630; CALL 01e0 -> returns to 01f0 (IMAD.IADD), 0960 -> returns to 0970 (NOP), 15d0 -> returns to 15e0 (BRA), 1620 -> returns to 1630 (NOP); helper `IMAD.MOV.U32 R13, RZ, RZ, 0x0 ; | WARPSYNC R15 ; | RET.REL.NODEC R12 `(_Z14cc_vertex_data8ECLgraphPiS0_PKiiS0_S0_iS0_) ;`; syncwarp records (all its recordings in the events store, both modes): full 0x200 1062, full 0x970 1062, full 0x1630 35904
- `CC_CUDA_V_Data_Pull_Determ_IntType_Persist_CudaAtomic_Warp_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug` (1 programs): NOPs 0250, 1140, 1e50; CALL 0230 -> returns to 0240 (IMAD.IADD), 1130 -> returns to 1140 (NOP), 1df0 -> returns to 1e00 (BRA), 1e40 -> returns to 1e50 (NOP); helper `IMAD.MOV.U32 R11, RZ, RZ, 0x0 ; | WARPSYNC R18 ; | RET.REL.NODEC R10 `(_Z14cc_vertex_data8ECLgraphPN4cuda3__46atomicIiLNS0_3std3__412thread_scopeE0EEES7_PKiiPiSA_iSA_) ;`; syncwarp records (all its recordings in the events store, both modes): full 0x250 1062, full 0x1140 1062, full 0x1e50 35904, partial 0x1e80 2548
- `CC_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_Atomic_Warp_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug` (1 programs): NOPs 0150, 10a0; CALL 1090 -> returns to 10a0 (NOP); helper `IMAD.MOV.U32 R7, RZ, RZ, 0x0 ; | WARPSYNC 0xffffffff ; | RET.REL.NODEC R6 `(_Z14cc_vertex_data8ECLgraphPiPKiiS0_S0_iS0_) ;`; syncwarp records (all its recordings in the events store, both modes): full 0x150 1062, full 0x10a0 1062, partial 0x1a10 2124
- `CC_CUDA_V_Data_Pull_NonDeterm_IntType_NonPersist_CudaAtomic_Warp_NoNbrBoundsBug_NoExcessThreadsBug_NoFieldBug_NoLivelockBug` (1 programs): NOPs 0180, 08c0; CALL 08b0 -> returns to 08c0 (NOP); helper `IMAD.MOV.U32 R9, RZ, RZ, 0x0 ; | WARPSYNC 0xffffffff ; | RET.REL.NODEC R8 `(_Z14cc_vertex_data8ECLgraphPN4cuda3__46atomicIiLNS0_3std3__412thread_scopeE0EEEPKiiPiSA_iSA_) ;`; syncwarp records (all its recordings in the events store, both modes): full 0x180 1062, full 0x8c0 1062, partial 0x1260 2548
- `CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_Atomic_Warp_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug` (1 programs): NOPs 0200, 1270, 1f30; CALL 01e0 -> returns to 01f0 (IMAD.IADD), 1260 -> returns to 1270 (NOP), 1ed0 -> returns to 1ee0 (BRA), 1f20 -> returns to 1f30 (NOP); helper `IMAD.MOV.U32 R11, RZ, RZ, 0x0 ; | WARPSYNC R15 ; | RET.REL.NODEC R10 `(_Z14cc_vertex_data8ECLgraphPiPKiiS0_S0_iS0_) ;`; syncwarp records (all its recordings in the events store, both modes): full 0x200 1071, full 0x1270 1071, full 0x1f30 29376
- `CC_CUDA_V_Data_Pull_NonDeterm_IntType_Persist_CudaAtomic_Warp_NoNbrBoundsBug_NoBoundsBug_NoFieldBug_NoLivelockBug` (1 programs): NOPs 0240, 0cb0, 19a0; CALL 0220 -> returns to 0230 (IMAD.IADD), 0ca0 -> returns to 0cb0 (NOP), 1940 -> returns to 1950 (BRA), 1990 -> returns to 19a0 (NOP); helper `IMAD.MOV.U32 R11, RZ, RZ, 0x0 ; | WARPSYNC R16 ; | RET.REL.NODEC R10 `(_Z14cc_vertex_data8ECLgraphPN4cuda3__46atomicIiLNS0_3std3__412thread_scopeE0EEEPKiiPiSA_iSA_) ;`; syncwarp records (all its recordings in the events store, both modes): full 0x240 1168, full 0xcb0 1168, full 0x19a0 31008, partial 0x19d0 2798

### C. Diverged-warp syncwarp instances (partial records) and the merged replay

| program | mode | launches | partial records (pc) | partial instances (2 / 3 records) | never completed | memory records of not-yet-arrived lanes | race pairs only after merge / only before | replay |
|---|---|---|---|---|---|---|---|---|
| P1-Pull_Determ_Persist_RaceBug-default-1296n | scalar-clock | 14 | 0x1730 13846 | 6923 / 0 | 0 | 0 | 0 / 0 | shared-only |
| P1-Pull_Determ_Persist_RaceBug-slower_atomic-1296n | scalar-clock | 14 | 0x1730 13796 | 6898 / 0 | 0 | 0 | 0 / 0 | shared-only |
| P1-Pull_NonDeterm_Persist_RaceBug-default-1296n | scalar-clock | 13 | 0x2010 13154 | 6577 / 0 | 0 | 0 | 0 / 0 | shared-only |
| P1-Pull_NonDeterm_Persist_RaceBug-slower_atomic-1296n | scalar-clock | 13 | 0x2010 13158 | 6579 / 0 | 0 | 0 | 0 / 0 | shared-only |
| P1-Push_NonDeterm_NonPersist_RaceBug-default-100n | scalar-clock | 12 | 0x1010 1488 | 744 / 0 | 0 | 1809 | 0 / 0 | full |
| P1-Push_NonDeterm_NonPersist_RaceBug-default-100n | vector-clock | 11 | 0x1010 1372 | 686 / 0 | 0 | 1700 | 0 / 0 | full |
| P1-Push_NonDeterm_NonPersist_RaceBug-default-1296n | scalar-clock | 11 | 0x1010 18960 | 9480 / 0 | 0 | 5985 | 0 / 0 | shared-only |
| P1-Push_NonDeterm_NonPersist_RaceBug-default-1296n | vector-clock | 10 | 0x1010 18478 | 9239 / 0 | 0 | 5811 | 0 / 0 | shared-only |
| P1-Push_NonDeterm_NonPersist_RaceBug-slower_atomic-100n | scalar-clock | 12 | 0x1010 1428 | 714 / 0 | 0 | 1744 | 0 / 0 | full |
| P1-Push_NonDeterm_NonPersist_RaceBug-slower_atomic-100n | vector-clock | 12 | 0x1010 1480 | 740 / 0 | 0 | 1826 | 0 / 0 | full |
| P1-Push_NonDeterm_NonPersist_RaceBug-slower_atomic-1296n | scalar-clock | 11 | 0x1010 19140 | 9570 / 0 | 0 | 6074 | 0 / 0 | shared-only |
| P1-Push_NonDeterm_NonPersist_RaceBug-slower_atomic-1296n | vector-clock | 10 | 0x1010 18532 | 9266 / 0 | 0 | 5865 | 0 / 0 | shared-only |
| P3-Pull_Determ_NonPersist_Atomic-100n | scalar-clock | 11 | 0x10a0 1062 | 531 / 0 | 0 | 812 | 0 / 0 | full |
| P3-Pull_Determ_NonPersist_Atomic-100n | vector-clock | 11 | 0x10a0 1062 | 531 / 0 | 0 | 812 | 0 / 0 | full |
| P3-Pull_Determ_NonPersist_CudaAtomic-100n | scalar-clock | 11 | 0x1600 1274 | 319 / 212 | 0 | 1555 | 0 / 0 | full |
| P3-Pull_Determ_NonPersist_CudaAtomic-100n | vector-clock | 11 | 0x1600 1274 | 319 / 212 | 0 | 1555 | 0 / 0 | full |
| P3-Pull_Determ_Persist_CudaAtomic-100n | scalar-clock | 11 | 0x1e80 1274 | 319 / 212 | 0 | 1024 | 0 / 0 | full |
| P3-Pull_Determ_Persist_CudaAtomic-100n | vector-clock | 11 | 0x1e80 1274 | 319 / 212 | 0 | 1024 | 0 / 0 | full |
| P3-Pull_NonDeterm_NonPersist_Atomic-100n | scalar-clock | 11 | 0x1a10 1062 | 531 / 0 | 0 | 281 | 0 / 0 | full |
| P3-Pull_NonDeterm_NonPersist_Atomic-100n | vector-clock | 11 | 0x1a10 1062 | 531 / 0 | 0 | 281 | 0 / 0 | full |
| P3-Pull_NonDeterm_NonPersist_CudaAtomic-100n | scalar-clock | 11 | 0x1260 1274 | 319 / 212 | 0 | 281 | 0 / 0 | full |
| P3-Pull_NonDeterm_NonPersist_CudaAtomic-100n | vector-clock | 11 | 0x1260 1274 | 319 / 212 | 0 | 281 | 0 / 0 | full |
| P3-Pull_NonDeterm_Persist_CudaAtomic-100n | scalar-clock | 10 | 0x19d0 1401 | 357 / 229 | 0 | 289 | 0 / 0 | full |
| P3-Pull_NonDeterm_Persist_CudaAtomic-100n | vector-clock | 9 | 0x19d0 1397 | 349 / 233 | 0 | 289 | 0 / 0 | full |

totals: {'groups': 60, 'groups with partial': 24, 'pending': 39298, 'after': 0, 'before': 0, 'errors': 0}
