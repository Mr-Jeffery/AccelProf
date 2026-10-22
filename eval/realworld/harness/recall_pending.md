
### 2.4 Pending, open and not scored (at this writing)

- **Not yet run or not yet usable:** `llamacpp-2/-4/-5` (void first run, re-queued after the fix in Defect 1), `cmssw-1` `certain` flavor (task landed on a node
  without BeeGFS), `raft-1-fixed` main flavor (queued as `t21b-fx-raft-1`), `amrex-1-fixed` and `hecbench-hungarian-1-fixed` (queued; the buggy
  runs of both ended ERROR/TIMEOUT, see below), the `vc5400` pass for `amrex-1-buggy` (queued). `raft-1` `certain` flavor: buggy done, fixed attribution running at 07:20.
- **m4 (TIMEOUT / ERROR) so far:** `amrex-1-buggy` (vector-clock TIMEOUT at 1,200 s; scalar-clock ERROR: analysis of 1,246 kernel JSONs exceeded
  `--analysis-timeout 3600`); `hecbench-hungarian-1-buggy` (both modes ERROR: about 6,900 kernel JSONs, analysis timeout). Not scored as detected or missed on the
  evidence; listed as m4 in `recall.csv`. A larger `--analysis-timeout` is a change to X1b's configuration: left for Jeffery.
- **Open decisions (REVIEW.md), scored by the oracle as committed:** `raft-1`, `cccl-3`, `cmssw-1` fixed builds (oracle: residual; under the fence + counter idiom
  reading, "absent", a fixed-build report on the residual pair would count STILL-REPORTED instead of RESIDUAL-AS-EXPECTED: see the fixed columns above);
  `hecbench-hungarian-1` and `hecbench-dxtc2-1` residual labels (same); `llamacpp-2` fixed build (ptxas compiled the added `__syncwarp` to a NOP; oracle
  "absent"). `llamacpp-open-2` is fixed upstream (`99db719bdf07`): pending, not run. Wave 3 and the 18 candidates are not built and not scored.
