# The reference algorithm in plain text

Convenience rendering for the coding agents. On any discrepancy the LaTeX sources in
this directory win: `hb_oracle_proof_v3.tex` (Algorithm 1, label `alg:hb`) and
`hb_defs_v4.tex` (Definition "Processing a record", steps (1)–(4)).

## A. Algorithm 1 — v3, the reference used by the proof

This is the text of the progress deck's slide "Algorithm 1 (reference used by the
proof)"; it is `alg:hb` stated in words.

```
State:  clock[t]            vector clock of thread t (clock[t][t] starts at 1)
        lastRelease[addr]   clock published by the last atomic on addr, with its scope and block
        lastWrite[loc]      last write on the location: (thread, epoch, pc)
        readers[loc]        reads since lastWrite: thread ↦ (epoch, pc)
        arrived[barrier]    lanes that have arrived at the open barrier instance

Sync(S):   J ← merge of clock[t] over t ∈ S;   for t ∈ S: clock[t] ← J;  clock[t][t] += 1
Check(e):  t ← thread(e); loc ← location(e)
           if lastWrite[loc] = (w, epoch_w, _) and w ≠ t and epoch_w > clock[t][w]:  report (w, e)
           if e writes: for each (r, epoch_r) in readers[loc] with r ≠ t and epoch_r > clock[t][r]:  report (r, e)

for each record e in trace order:
   exit                  do nothing
   warp sync             Sync(lanes of e)
   barrier arrival       arrived[k] ∪= lanes(e);  if |arrived[k]| = expected: Sync(arrived[k]); arrived[k] ← ∅
   atomic by t on addr   if lastRelease[addr] covers t: clock[t] ← clock[t] ⊔ lastRelease[addr]      (acquire)
                         Check(e);  lastRelease[addr] ← clock[t];  record as write;  clock[t][t] += 1  (publish, then tick)
   write by t            Check(e);  lastWrite[loc] ← (t, clock[t][t], pc);  readers[loc] ← ∅
   read by t             Check(e);  readers[loc][t] ← (clock[t][t], pc)
```

Details fixed by the `.tex` and not visible above:

- `covers(r, e)`: with s = min(scope(r), scope(e)), true iff s = Grid, or s = Block and
  the two threads are in the same block. Scopes come from the static sidecar
  (`AtomScope[pc]`), None < Block < Grid.
- `expected` for a barrier arrival is n(A) if n(A) > 0, else the block size N_β.
  Instances are assembled per key (block, bar) from per-warp arrival records
  (Definition "Expected count, instances"); a trailing incomplete segment never fires.
- `location` = (shared, block, addr) | (local, thread, addr) | (global, addr).
- "record as write" = `lastWrite[loc] ← (t, epoch, pc); readers[loc] ← ∅` with
  epoch = clock[t][t] **before** the tick.
- Correspondence with `python/hb_oracle.py`: clock = `vc`, lastRelease = `released`,
  lastWrite = `last_write`, readers = `last_reads`, Sync = `sync_group`,
  arrived = `pending_bar`.
- Well-formedness W0–W2 and the monitor (TV checks) are Definitions "Well-formed trace"
  and "Well-formedness monitor".

## B. Revision 4 — the newest algorithm (proposal, not implemented)

Record labels (Definition "Record labels"): kind ∈ {R, W, RMW}; str ∈ {weak, strong}
(RMW is always strong); scope ∈ {cta, gpu, sys} for strong records; for RMWs the static
flags rel, acq ∈ {0, 1} from fence adjacency (Definition "Fence adjacency"); warp and
issue group from the collector.

Moral strength: ms(a, b) iff both strong, incl(a, tid(b)) and incl(b, tid(a)), where
incl(e, t) iff scope(e) ∈ {gpu, sys}, or scope(e) = cta and same block.

Verdicts (Definition "Conflict, unordered, verdicts"), for seq(a) < seq(b):

```
conf(a,b)  := loc(a)=loc(b) ∧ tid(a)≠tid(b) ∧ (kind(a)≠R ∨ kind(b)≠R)
unord(a,b) := ¬(a →hb b) ∧ ¬(b →hb a)
DR(a,b)    := conf ∧ unord ∧ ¬ms(a,b)                              data race (PTX §8.7.1)
SC(a,b)    := conf ∧ unord ∧ ms(a,b) ∧ ¬(kind(a)=kind(b)=RMW)     unordered strong conflict
```

Happens-before: (PO) and (SYNC) as in v3; (ATOM) r →hb q iff r ⇝ q (a release chain:
successive RMWs on one location, every link morally strong), rel(r) = 1 and acq(q) = 1.
HB⁺ is the same with (ATOM) read as r ⇝ q only (used for the MS label).

Per-location state (Definition "Per-location state"): buckets B_x[u, κ] for every
thread u and key κ = (kind, str, scope) holding u's latest (epoch, pc) on x with that
key; a chain clock C_x (a vector clock or ⊥) and last_x = (tid, scope, blk) of the last
RMW on x.

Processing a record a of thread t on location x (Definition "Processing a record"):

```
(1) chain step (RMW only)   if last_x exists and ¬ms(last_x, a): C_x ← ⊥
                            if acq(a) = 1 and C_x ≠ ⊥: vc[t] ← vc[t] ⊔ C_x
(2) checks                  for every u ≠ t and every key κ with an entry e = B_x[u, κ]:
                              if (kind(e) ≠ R ∨ kind(a) ≠ R) and epoch(e) > vc[t][u]:
                                report (e, a): class DR if ¬ms(e, a);
                                               class SC if ms(e, a) and not both RMW;
                                               nothing otherwise
(3) record                  B_x[t, key(a)] ← (epoch(a), pc(a))
(4) publish and tick (RMW)  if rel(a) = 1: C_x ← (C_x or ⊥) ⊔ vc[t]
                            last_x ← (t, scope(a), blk(t));  vc[t][t] += 1
```

Arrivals, departures and exits as in v3. epoch(e) = number of ticks of tid(e) that
precede e in program order; publishing happens before ticking, as in v3. The v3 state
is the special case: all records weak except RMWs, one write bucket per location,
C_x = released[loc]. Implementation obligations O1–O6 are listed at the end of the file
(sidecar strength/scope, the fence inventory for the target SM, fence adjacency, buckets
in engine and oracle, trace fields, litmus additions).

## C. Record kinds the code has added since (as implemented, not in either proof)

From T1a (merged 2026-09-23; `eval/CP_ASYNC_REPORT.md`):

- `pipeline_commit` and `pipeline_wait` events, one per warp, emitted only under
  `YOSEMITE_HB_TRACE`.
- An LDGSTS (`cp.async`) copy's shared write is performed by the issuing thread's async
  agent, id `tid | 1<<62`, ordered after the thread's earlier accesses. Each
  `commit_group` snapshots the agent's clock and ticks the agent; `wait_group N` joins
  the snapshot of the newest group it completes into the thread's clock. Same model in
  `HbEngine`, `hb_oracle.py` and `barrier_only_pairs`; race records keep the thread's id
  and carry `"async": "a" | "b" | "ab"`; dumps with the model carry `"hb_async": 1`.
- Two copies of one thread to one location are checked against the issuing thread's
  view of its agent (same-tid pairs are no longer skipped for copies).
- Static rules (scalar-clock mode): no R1/R2 credit when the earlier access is a copy,
  no R3 credit to a pair with a copy; `--assume-warp-lockstep` never orders a record
  involving a copy. Copies completed through an mbarrier keep the pre-T1a reading
  until T1b.

T6 states these as an extension of the v3 trace model (new event kinds, their program
order, two new HB generators) so that T9 can check that `thm:complete` and `thm:sound`
still hold with them.
