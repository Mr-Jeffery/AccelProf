# The instance gate (T12, I4): design note

Scope: `hb_proof.tex` Definition "Gate" (the instance gate) and §5's R3 amendments, implemented
in `python/sync_dominance.py` (the predicate, R3), `python/atomic_scope_sidecar.py` (the table the
engine reads), `python/hb_oracle.py` and `HbEngine` (the (ATOM) generator), and
`design/algorithms_check.py` (the direct-evaluation reference). Written before the code; the
sections marked *decision* are the choices the proof leaves open.

## 1. The predicate

`fenced(p, p', s, side)`: every CFG path from pc `p` to pc `p'` crosses an instruction that is a
fence of scope ≥ `s` on `side` (release or acquire). Evaluated on an **instruction-level** graph
built from the nvdisasm `-bbcfg` dot (the same parse as `HBGraph`): an edge from each instruction
to the next one in its basic block, from a block's last instruction to the first instruction of
each successor block; an unpredicated `EXIT`/`RET` has no successor. A path is non-empty, so
`fenced(p, p, …)` asks whether every cycle through `p` crosses a fence (the spin-loop case: a
failed CAS followed by the next attempt of the same CAS).

Computation: `p'` is *not* fenced from `p` iff `p'` is reachable from a successor of `p` through
non-fence instructions (a fence node is neither entered nor expanded), `p` and `p'` themselves
not being fences. One BFS per (source, side, scope), memoised per kernel.

**Endpoints (open point of the brief).** A path that starts or ends *at* a fence crosses it. The
only records whose pc can be a fence are barrier arrivals (`BAR.SYNC`); memory records never are.
A barrier arrival has no memory effect of its own that the fence would have to order, and PTX
gives `bar.sync` the ordering of a `cta` fence at the arrival itself: for `rel(r)` with the
previous record a barrier, everything of `t` before the arrival is ordered before it, hence
before `r`; for `acq(r)` with the next record a barrier, everything of `t` after the arrival is
ordered after it. So an endpoint barrier counts, for scope `cta`.

**Unknown pcs.** A record pc absent from the CFG (never observed; would be an alignment failure
elsewhere) makes `fenced` false: the gate errs toward reporting (Lemma "Monotonicity").

**Predicated fences.** `@P MEMBAR…` may not execute; it is not a fence. (None in the kept CFGs;
the parser keeps the predicate so the rule is enforced rather than assumed.)

## 2. The fence inventory (O2), sm_89 and sm_86

From T6's scan of the 293 kept sm_89 CFGs and a probe compiled for this task
(`eval/instance_gate/o2_probe.cu`, CUDA 13.3 `nvcc -arch=sm_89|sm_86 -cubin`, node c39;
listing `eval/instance_gate/o2_probe.sm_89.sass.txt`; the two architectures lower identically):

| PTX | SASS |
|---|---|
| `fence.sc.cta` (`__threadfence_block`) | `MEMBAR.SC.CTA` |
| `fence.acq_rel.cta`, `fence.acquire.cta`, `fence.release.cta` | `MEMBAR.ALL.CTA` |
| `fence.sc.gpu` (`__threadfence`) | `MEMBAR.SC.GPU; ERRBAR; CCTL.IVALL` |
| `fence.{acq_rel,acquire,release}.gpu` | `MEMBAR.ALL.GPU; ERRBAR; CCTL.IVALL` |
| `fence.sc.sys` (`__threadfence_system`) | `MEMBAR.SC.SYS; ERRBAR; CCTL.IVALL` |
| `atom.release.gpu` / `.sys` | `MEMBAR.ALL.{GPU,SYS}; ERRBAR; ATOM…` |
| `atom.acquire.gpu` / `.sys` | `ATOM…; CCTL.IVALL` |
| `atom.acq_rel.gpu` | `MEMBAR.ALL.GPU; ERRBAR; ATOM…; CCTL.IVALL` |
| `atom.seq_cst.gpu` | `MEMBAR.SC.GPU; ERRBAR; CCTL.IVALL; ATOM…; CCTL.IVALL` |
| `atom.release.cta` / `atom.acq_rel.cta` | `MEMBAR.ALL.CTA; ATOM…` |
| **`atom.acquire.cta`, `atom.relaxed.cta`** | **`ATOM…` — identical, nothing emitted** |
| `bar.sync` | `BAR.SYNC(.DEFER_BLOCKING)`, never with an adjacent fence (T6: 461/461) |

The inventory, per side (`sync_dominance.fence_scope`):

| instruction | release side | acquire side |
|---|---|---|
| `MEMBAR.{SC,ALL}.CTA` | block | block |
| `MEMBAR.{SC,ALL}.{GPU,SYS}` | grid | grid |
| `CCTL.IVALL` | — | grid |
| `BAR.SYNC*`, `BAR.RED*` | block | block |
| anything else (`ERRBAR`, `WARPSYNC`, `DEPBAR`, a predicated fence, …) | — | — |

A `MEMBAR` counts on the acquire side because the PTX fence it lowers from (`fence.sc`,
`fence.acq_rel`, `fence.acquire`) is an acquire fence; on the gpu/sys scopes it is always followed
by `CCTL.IVALL` anyway. `CCTL.IVALL` does not count on the release side: an acquire load
(`LD…STRONG; CCTL.IVALL`) before an RMW does not make the RMW a release.

**The open O2 point, answered: a `cta`-scope acquire emits nothing.** `atom.acquire.cta` and
`atom.relaxed.cta` (and the CAS forms) compile to the same instruction with no fence, on both
architectures. The binary therefore cannot tell a cta acquire RMW from a relaxed one. *Decision:*
the gate reads the binary and sets `acq(r) = 0` for such an RMW unless an explicit fence (a
`MEMBAR.*.CTA`, a barrier, or a wider fence) follows it on every path — the direction Lemma
"Monotonicity" allows (more reports, never fewer). Cost: a program that relies on a libcu++
`thread_scope_block` acquire with no fence gets reports. The corpus's block locks use the legacy
`atomicCAS_block` + `__threadfence_block()` idiom (`MEMBAR.SC.CTA`), which is gated correctly; the
measurement (§7) lists every program where a cta-scope RMW lost its acquire. A `cta` *release*
does emit `MEMBAR.ALL.CTA`, so the release side has no such gap.

## 3. rel and acq on a trace

For an RMW record `r` of thread `t`, with `p` / `q` the `PO`-previous / `PO`-next record of `t`:

- `rel(r) = 1` iff `p` does not exist or `fenced(pc(p), pc(r), scope(r), release)`;
- `acq(r) = 1` iff `q` does not exist or `fenced(pc(r), pc(q), scope(r), acquire)`.

"Record of any kind": memory records, barrier arrivals (`pc` = the `BAR`), syncwarp, pipeline
commit/wait and exit records (`pc` = the `EXIT`) all count; `local` records do not (they are
outside the model, D14, and the T9 collector no longer emits them, so an older dump must replay
as a newer one would). `q` "does not exist" only at the end of the kernel, as in the proof. An
RMW whose scope is `none` (no scope token) is never `ms` with anything, so its chain is broken on
both sides and the gate is irrelevant; it gets `rel = acq = 1` (no effect).

## 4. The sidecar (what the engine reads)

The engine cannot run a CFG search. Per kernel and per RMW pc `r` with scope `s ∈ {block, grid}`,
`atomic_scope_sidecar.py` writes the **fenced** record pcs on each side:

```
# gate-kernel <kernel>
# gate <r> rel <kernel> <p1> <p2> ...      p with fenced(p, r, s, release)
# gate <r> acq <kernel> <q1> <q2> ...      q with fenced(r, q, s, acquire)
```

over the kernel's record-able pcs (memory instructions, `BAR`, `WARPSYNC`, `EXIT`/`RET`,
`LDGDEPBAR`/`DEPBAR`). The engine takes `rel(r) = 1` iff `pc(p)` is listed on `r`'s `rel` line (or
`p` does not exist), and the same for `acq`; a pc not listed — including one the table does not
know — is unfenced, so a gap in the table can only add reports. Listing the fenced pcs rather than
the unfenced ones is what makes the unknown case conservative. Comment lines: an engine older than
T12 skips them. A sidecar without any `# gate-kernel` line (pre-T12) leaves the engine on the
trusting gate, because an absent table would otherwise read as "nothing is fenced". Both the
sidecar and the oracle compute the table with one function, `sync_dominance.gate_table`, so they
cannot disagree.

Selection: `YOSEMITE_HB_GATE=instance|trusting` (engine), `--gate` / `$CUVEIN_GATE` (oracle,
`hb_oracle.analyze(gate=…)`), default `instance`. The engine writes `"hb_gate": "instance"` or
`"trusting"` into the dump next to `hb_races`, and the oracle, when not told otherwise, replays a
dump with the gate that produced it: a dump without the key (every pre-T12 dump) replays under the
trusting gate, so an old store re-scores unchanged unless `--gate instance` is given (which is
what §7's measurement does).

## 5. The chain clock becomes a join

`released[loc]` holds the chain clock `Ch_ℓ` (or ⊥) plus the label of the last RMW on `ℓ`
(block, scope). At an RMW `r` of `t`:

1. chain broken (the last RMW is not `ms` with `r`) → `Ch_ℓ ← ⊥`;
2. acquire `J = Ch_ℓ` if `acq(r) = 1` (deferred in the engine, §6);
3. `Check(r)`, bucket;
4. publish `Ch_ℓ ← (Ch_ℓ or ∅) ⊔ clk[t]` iff `rel(r) = 1`; the label becomes `r`'s regardless;
5. tick.

Under the trusting gate this is today's overwrite (`clk[t]` already contains `Ch_ℓ` unless the
chain broke, when `Ch_ℓ = ⊥`), so the trusting path keeps today's code unchanged. Under the instance
gate a non-releasing RMW leaves `Ch_ℓ` as it was, so a later acquirer still gets the chain's
earlier releases through it (Definition "Gate": `r ⊸ q` spans intermediate RMWs; only the
endpoints need `rel`/`acq`).

## 6. The engine's deferred acquire (T6's four points)

The online engine learns `pc(q)` only when `t`'s next record arrives. The T14 machinery already
has exactly this event: every RMW opens a *window* that `t`'s next record (memory lane, barrier,
syncwarp, pipeline, exit) or the end of the kernel closes (`a2_open` / `a2_close`). The gate state
lives in that window:

- **(1) `Check(r)` against `clk[t] ⊔ J`.** At `r`, `J` is held, not joined. `Check(r)` walks the
  buckets as always against `clk[t]`; a conflicting entry `e` with `e.epoch ≤ J[u]` (ordered only
  if the acquire happens) is *held* in the window instead of reported; every other unordered
  conflict is reported at once. At the close: `acq(r) = 1` → join `J` into `clk[t]` (and `J`'s
  possible-clock part into `pd[t]`), drop the held pairs; `acq(r) = 0` → report the held pairs.
  Nothing else reads `clk[t]` between `r` and `t`'s next record (proof §3): other threads see `t`
  only through `Ch_ℓ` and through barrier instances `t` enters with a later record, and every
  consumer of `t`'s next record runs after the close. The barrier-only clock has no (ATOM) and is
  untouched.
- **(2) `released[loc]` becomes a join** (§5). With the join, the publish at `r` yields
  `Ch_ℓ ⊔ clk[t]` whether or not `J` has been joined yet, since `Ch_ℓ ⊇ J`.
- **(3) No publish when `rel(r) = 0`.** `rel(r)` needs only `t`'s previous record, which the
  engine has: it keeps each thread's last record pc (per warp, 32 slots; only while the kernel
  has RMW pcs).
- **(4) Held pairs are resolved at kernel end** with `acq(r) = 1` (`q` does not exist), before
  `hb_races` is written (`emit` → `a2_close_all`).

The oracle mirrors the deferral step for step instead of evaluating `acq` at `r`. Its race *set*
is the same either way (the argument above, and §8's reference check proves it on the traces);
mirroring keeps the aggregated records, their counts and their T14 `a2_uncertain` counts
identical to the engine's, which the parity tests compare.

**T14's flag under the gate.** The possible clock follows the gate: `pd` joins the held part only
if `acq(r) = 1`, a window's late acquire (its cluster component's join) only if `acq(r) = 1`, a
member contributes to its component and hands on only if `rel(r) = 1`. So a pair left unordered
because a fence is missing is not flagged as A2-uncertain unless a reversal could order it
through gated edges. Under the instance gate the flag decisions of `Check(r)`'s reports are taken
at the close, after the gate is resolved (they depend on `J` through `pd`). One consequence,
measured in §7 rather than argued away: when the other endpoint `u`'s RMW window was open at `r`
but closes before `t`'s next record, the decision can no longer be held on `u`'s window and is
taken on `t`'s alone — a possible under-flag relative to T14's definition, informational only (the
flag moves no verdict). Under the trusting gate nothing changes.

## 7. R3 (`HBGraph.chain`)

- **Release point from the trace.** For a non-atomic access pc `u`, the start of the chain is the
  `PO`-next RMW of `u`'s thread after each observed instance of `u` (from `hb_events`, lane by
  lane). R3 may start only if every instance has one; the release scope of a start `a` is the
  largest `s` with `fenced(u, a, s, release)`; if the instances disagree on `a`, a chain must exist
  from every one of them. This replaces `release_scope` (a `MEMBAR` in postdom(u) ∩ dom(a)) and
  its region-dominance program order for the release point. A dump without `hb_events`, or above
  `CUVEIN_BARRIER_PASS_MAX_LANES`, keeps the region test (said in the report).
- **Acquire point from the trace** (added during the measurement; not in the brief's step 3).
  The release point alone did not certify the 23 pairs it was meant to: in `rule-110-norace`
  the reader `v` sits under a loop/branch too, so the old acquire test `po(n, v)` (region
  dominance) fails for every atomic even when the release side is certified. Symmetric to the
  release point: the chain must land (after a sync hop, not past the section's release) on the
  `PO`-previous RMW of `v`'s thread in each observed instance of `v`; an instance with no RMW
  before it cannot be acquired. The acquire side stays fence-agnostic, as R3 was (a flag
  hand-off is ordered by the dependency on the spin; ScoRD's reading; the vector clock's gate is
  where the acquire fence is required). Ablation `CUVEIN_R3_TRACE_ACQUIRE=0`.
- **Covering rule.** With trace points on either side, `anc`'s instances can release at
  different RMWs and `cur`'s acquire at different ones (rule-110: border threads hand off
  through a grid-scope `EXCH`/`ADD` pair, inner threads through block-scope ones). R3 requires
  every release start to reach some acquire point and every acquire point to be reached from
  some start. The pre-T12 rule was "some start reaches some acquire"; the cross product
  (every start to every acquire point) rejects rule-110's correct pairing. It is still a
  pc-level rule that assumes the observed hand-offs are the ones the instances used.
- **The acquire side of a CAS section** (`_cs_fenced`: a store in a CAS critical section needs a
  fence after the CAS) uses the same predicate, `fenced(c, x, need, acquire)`, in place of
  `release_scope(c, x)`: a fence on the success branch only now counts (Finding 1 of T9-0,
  `matrix-multiplication`).
- **Write-before-lock decline**, the mirror of `_past_release`: R3 declines when `u` precedes, in
  its own thread, a CAS acquire on the location from which the chain's first hop departs
  (`u -po-> c` with `c` that hop's atomic or observed on its location). Ablation:
  `CUVEIN_R3_BEFORE_ACQUIRE=0`.

## 8. Checks

- `design/algorithms_check.py` gains the instance gate evaluated **directly** (look-ahead to `q`,
  no deferral): Detect(T, vec) with the instance gate must equal the oracle's `race_records` on
  every litmus trace — this is the test of the deferral argument.
- Unit tests of `fenced` on the kept litmus CFGs (success-branch fence; failed CAS; fence hoisted
  before a loop; barrier endpoints).
- `test_relaxed_handoff_should_race` loses its strict-xfail marker in the same commit.
- Parity: engine == oracle on the green set, with the gate on.

## 9. What is not done here

The per-lane monitor (I6), the obligation "if some RMW on ℓ releases, every write on ℓ is an RMW"
(proof §7, obligations kept from v4), `cp.async`/bulk agents (I7), and SM architectures other than
sm_86/sm_89 (the inventory is per architecture; sm_90's `FENCE.VIEW.ASYNC` and friends are T1b's).
