# T21c triage: pcl-new-1 (PCL 66e1d0ea8cc3fa54820eb38e18ad0adac6345b94, `EstimateNormalsKernel` / `NormalsEstimator::operator()`)

Inputs: `eval/results/realworld_t21c/attrib/pcl-new-1-buggy.json` (scalar-clock, 1 kernel JSON, 657 reports, 0 SC, 0 ordered,
337 skipped), `other_reports.csv` (381 rows), `recall.csv` (DR component DETECTED, SC component DETECTED-AS-DR), racecheck
`eval/realworld/racecheck/pcl-new-1-buggy.txt`, SASS of the traced build (`/mnt/beegfs/fzheng4/realworld_t21c/build/pcl-new-1/buggy/driver`,
md5 71c1613b0f71368b9f9f9864f7ad35e2; `lineinfo.check`: SAME), trace edges of `kernel_0.json`. Launch: 1,000 points, 40 neighbours,
`<<<125, 256>>>`, one warp per point. Grouping: by the normal_3d.cu statement each access belongs to (outermost frame below the
kernel wrapper L183), then by innermost line pair; scripts `grp2.py`/`grp3.py` in the triage scratchpad.

Row layout (per warp, base = tid - lane): `cov_buffer[r][base + j]`, r = 0..5, j = 0..31; the centroid reductions use row 0
as `buffer`; Eigen33 gets `mat_pkg = cov = row 0`, `tmp = row 1`, `vec_tmp = row 2`, `evecs = row 3` (each a Mat33 = elements 0..8).
Every report is intra-warp: all addresses are in the warp's own 32 columns, and the trace edges of the reported pairs are
`intra_warp` (967,000) or `intra_thread` (6,000), never intra-block.

## Groups

| # | statements (normal_3d.cu) | pcs (a / b) | innermost line pairs | n | other | class | reason |
|---|---|---|---|---|---|---|---|
| P1 | within each 3-arg Warp::reduce, L103 / L104 / L105 | 0x9d0..0xb00, 0xb20..0xc50, 0xc70..0xda0 | warp.hpp:164 STS -> 168..172 LDS; 168..172 STS -> next LDS (RAW); 169..172 LDS -> 169..172 STS (WAR); 172 STS -> 174 LDS | 60 | 6 | (a) | lane l+k stores buffer[l+k], lane l loads it in the next step (or the same step's store by lane l+k follows lane l's load); volatile both sides. Oracle SC pair L164 -> L168 |
| P2 | L103 -> L104, L104 -> L105 (consecutive centroid reduces) | a 0xa00..0xb00 / b 0xb20..0xc30; a 0xb50..0xc50 / b 0xc70..0xd80 | warp.hpp:168..172, 174 LDS -> 164, 168..171 STS, WAR | 42 | 6 | (a) | lane m reads buffer[0] (L174, c.x result) or buffer[l+k] while lane 0 / lane l already stores the next reduce's init at L164 or its next step; nothing between the two reduces |
| P3 | L105 -> L115, L105 -> L124 (c.z reduce -> cov zeroing / cov store, across `__threadfence_block` L109) | a 0xca0..0xda0 / b 0xea0, 0x19b0 | warp.hpp:168..172, 174 LDS -> normal_3d.cu:115 STS, :124 STS, WAR | 12 | 10 | (a) | lane m reads buffer[0] = cov_buffer[0][base] at L174 while lane 0 stores 0 there at L115 (and the final cov00 at L124); `MEMBAR.SC.CTA` in both lanes does not order a load before another lane's later store (see below). The upstream comment at L108 records a wrong value here |
| P4 | L105 -> L132 (row-0 reduce stores), -> L141, -> Eigen33 L224 | a 0xcd0..0xda0 / b 0x1ae0..0x1ba0, 0x21d0, 0x2390 | warp.hpp:169..172, 174 LDS -> warp.hpp:152..156 STS, normal_3d.cu:141 STS, eigen.hpp:224 STS, WAR | 17 | 17 | (a) | c.z-reduce reads of row 0 vs later stores to row 0 by other lanes |
| P5 | L124..L129 -> L132..L137 (cov accumulation -> row reduce) | a 0x19b0..0x1a00 / b 0x1ac0..0x2170 | normal_3d.cu:124..129 STS -> warp.hpp:152..156 LDS (`buffer[lane+k]`, via the `plus` functor normal_3d.cu:64), RAW | 30 | 12 | (a) | lane l+k's plain store of its partial cov (register-accumulated, one STS per row) vs lane l's volatile load. Oracle DR pair L124 -> L152 |
| P6 | within each 2-arg Warp::reduce, L132..L137 | 0x1ae0..0x1ba0, 0x1c10..0x1cd0, 0x1d40..0x1e00, 0x1e70..0x1f30, 0x1fa0..0x2060, 0x20d0..0x2190 | warp.hpp:152..156 STS -> next LDS (RAW, 4 per row), 153..156 LDS -> 153..156 STS (WAR, 10 per row) | 84 | 0 | (a) | as P1 for the six covariance rows |
| P7 | L132..L137 -> L141 (row reduces -> lane<6 gather) | a 0x1b20..0x1b80, 0x1cd0, 0x1e00, 0x1f30, 0x2060, 0x2190 / b 0x21d0, 0x21b0 | warp.hpp:154..156 LDS -> normal_3d.cu:141 STS (WAR, row 0); warp.hpp:156 STS -> normal_3d.cu:141 LDS (RAW, rows 1..5) | 8 | 0 | (a) | lane 1..5 overwrites row0[1..5] (L141) while lane 0 still reads them in the row-0 reduce; lane 0's final row-r store (L156) vs lane r's plain read of cov_buffer[r][base] at L141 |
| P8 | L132..L135 -> Eigen33 (L155, lane 0 only) | a 0x1a70..0x1f30 / b 0x2480..0x61a0, 0x62f0, 0x6300 | warp.hpp:148, 154..156 LDS and 156 STS -> eigen.hpp:224..229, 319..434 STS (via tmp/vec_tmp/evecs and mat_pkg), vector_math.hpp:76 LDS, normal_3d.cu:167/168 LDS; WAR, WAW, RAW | 330 | 330 | (a) | lanes 1..8 read and write elements 1..8 of rows 0..3 inside the reduces; lane 0 later overwrites (tmp/vec_tmp/evecs, mat_pkg /= scale) and reads them in Eigen33. No ordering between lane k's reduce access and lane 0's Eigen access |
| P9 | L141 -> Eigen33 | a 0x21b0, 0x21d0 / b 0x2200..0x5ff0 | normal_3d.cu:141 STS -> eigen.hpp:215..217, 225..229, 427..434 LDS (RAW) and 225..229 STS (WAW); normal_3d.cu:141 LDS -> eigen.hpp:319..434 STS (WAR) | 74 | 0 | (a) | lanes 1..5 store cov[1..5] = row0[1..5] (L141) that lane 0 reads as mat_pkg[1..5] and rescales; lanes 1..5 read row r[0] (r = 1..5) at L141 that lane 0 overwrites as tmp/vec_tmp/evecs |

Totals: 657 reports, 657 class (a), 0 (b), 0 (c), 0 (d). The 381 `other_reports.csv` rows: P1 6, P2 6, P3 10, P4 17, P5 12,
P8 330 (sum 381); all class (a), all the same mechanism as the oracle pairs (lanes of one warp exchanging data through shared
memory with no `__syncwarp`), so no new distinct race beyond the finding `findings/pcl-new-1.md`, which covers all groups
(P3 and P8/P9 are called out there). No benign/same-value group: every conflicting pair carries different values (the one
same-value candidate, lane 0's own L141 copy `cov[0] = cov_buffer[0][base]`, is intra-thread and not reported). No report
matches the LDS vs ATOMS.CAST.SPIN false-report class.

## Mechanism and ordering (all groups)

PCL's `Warp::reduce` (warp.hpp L144-L175) is the pre-Volta warp-synchronous tree over a `volatile T*`, with
`if (lane < 16)` around the five steps and no `__syncwarp`; at the pinned commit there is no `__syncwarp` anywhere under
`gpu/` (`git grep`). Thread pairs, block 0 warp 0 (racecheck shows the same with threads 112/96 of warp 3): lane 16 stores
`buffer[16] = c.x` at L164, lane 0 loads `buffer[16]` at L168 (P1); lane 16 stores `cov_buffer[0][16]` at L124, lane 0 loads it
at L152 (P5); lane 5 loads `buffer[0]` at L174, lane 0 stores `cov_buffer[0][0] = 0` at L115 (P3); lane 1 stores `cov[1]` at
L141, lane 0 reads `mat_pkg[1]` at eigen.hpp:215 (P9). Same warp; nothing orders them in PTX: no barrier, no
`bar.warp.sync`, no shuffle between the accesses.

SASS (traced build): every volatile access is kept and plain. 3-arg reduce: `STS [R21]` + `LDS [R21]` (L164; the C++
`T val = buffer[lane] = init` reads the volatile back), five `LDS [R6.X4+0x40/0x20/0x10/0x8/0x4]` + `STS [R21]` (L168-L172),
`LDS [R18.X4]` (L174). 2-arg reduce: `LDS` (L148), five LDS+STS. The cov accumulation L124-L129 is kept in registers by
ptxas (plain `+=`) and stored once per row at 0x19b0..0x1a00; the L115 zero stores remain (0xea0..0xf40). Each
`if (lane < 16)` block is bracketed by `BSSY B0 ... BSYNC B0`; `__threadfence_block()` is `MEMBAR.SC.CTA` (0xe90); there is
no WARPSYNC in the kernel. After L141 (`@!P0 LDS; @!P0 STS`, predicated) lanes 1-31 `EXIT` (0x21e0) and lane 0 runs
Eigen33 alone. So on this build every cross-lane pair is separated by a BSYNC reconvergence point or by EXIT, or executes in
one converged instruction stream: formal only (see the dossier for the perturbation design).

P3 and the fence. Under PTX, `fence.sc.cta` in lane m (after its L174 load) and in lane 0 (before its L115 store) orders the
pair only in executions where lane m's fence precedes lane 0's in Fence-SC order (then the fences synchronize); in executions
with the opposite Fence-SC order nothing relates the load to the store, so the program still has a racy execution. Class (a),
not (b). The upstream comment "nvcc bug workaround. if comment this => c.z == 0 at line: float3 d = fetch(*t) - c;" (L108,
present since the file moved in 0b39f15ad, 2012) describes a wrong value of c.z when the fence is absent, which is what this
WAR would produce if lane 0's L115 store were performed before another lane's L174 load. Whether that 2012 symptom came from
this race or from a compiler bug was not determined.

## Not checked

`principal_curvatures.cu`, `fpfh.cu` (same pattern per the record) and the kinfu kernels were not built or traced. The
`size < MIN_NEIGHBOORS` path (only lane 0 returns, L86-L91) is not exercised by the driver (all sizes 40).
