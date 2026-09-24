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

## D. Algorithm 1 as implemented at `cuVein` 3331d35 — derived from `python/hb_oracle.py`

`HbEngine` is the 1:1 port of this (parity-tested). Lines marked `≠ v3` differ from
section A; everything else is section A. Written 2026-09-24 from the code, not from the
proof; T6 reviews it and adds the scalar-clock algorithm.

```
Static inputs (CFG + sidecar):
    atom_scope[pc]   scope of an RMW pc: NONE < BLOCK < GRID          (v3's AtomScope)
    coh_scope[pc]    coherence scope of a "coherent" pc: RMWs plus, per policy
                     --strong-ldst (default generic), .STRONG loads/stores     ≠ v3
    async_pcs        LDGSTS (cp.async) pcs — used only if the dump carries hb_async   ≠ v3
    block_tc         block_thread_count of the kernel

State:
    vc[t]            vector clock (barriers + atomic hand-offs); own component starts at 1
    vs[t]            second clock advanced by barriers/syncwarps ONLY                 ≠ v3
    released[loc]    (clock, block, scope) of the last RMW on loc; loc = (shared, block, addr)
                     or (global|local, addr)                        ≠ v3 (v3: by address)
    last_write[loc]  (tid, epoch, sepoch, pc, coh, block)          coh, block, sepoch ≠ v3
    last_reads[loc]  tid ↦ (epoch, sepoch, pc, coh, block)
    pending_bar[(block, bar)]  arrived tids of the open instance
    groups[t]        snapshots (vc, vs) of t's async agent, one per commit_group, oldest first  ≠ v3
    ASYNC = 1<<62;  agent(t) = t | ASYNC

own(t):   if vc[t][t] = 0: vc[t][t] ← 1;  return vc[t][t]         (owns(t): same on vs)
coherent(c1, b1, c2, b2):  c1, c2 both defined ∧ (min(c1,c2) = GRID ∨ (min = BLOCK ∧ b1 = b2))
Sync(S):  for C in (vc, vs): J ← ⊔_{t∈S} C[t];  for t ∈ S: C[t] ← J;  C[t][t] ← J[t] + 1
Conflict(prev, cur, observer o = tid(cur)):                         two tests, one per clock
          if prev.epoch  > vc[o][prev.tid]: report (prev, cur)              → races
          if prev.sepoch > vs[o][prev.tid]: sync_pairs[{prev.pc, cur.pc}] += 1  → races_sync_only  ≠ v3

for each record e in seq order (TV-seq-monotonic: seq strictly increasing):
   pipeline_commit (lanes)        for each lane t: ag ← agent(t); own(ag); owns(ag);
                                  groups[t].append(copy(vc[ag]), copy(vs[ag]));
                                  vc[ag][ag] += 1;  vs[ag][ag] += 1                       ≠ v3
   pipeline_wait N (lanes)        for each lane t: if |groups[t]| > N:
                                  done ← |groups[t]| − N;  (svc, svs) ← groups[t][done−1];
                                  vc[t] ⊔= svc;  vs[t] ⊔= svs;  drop groups[t][0:done]   ≠ v3
   syncwarp                       Sync(masked lanes)
   barrier arrival                arrived ← pending_bar[(block, bar)] ∪ active lanes;
                                  expected ← thread_count or block_tc;
                                  TV-overfill: |arrived| > expected → reject;
                                  if not expected or |arrived| ≥ expected:
                                      TV-expected-nonzero-multiwarp: unknown count ∧ >1 warp → reject;
                                      Sync(arrived); pending_bar[(block, bar)] ← ∅
                                  else mark the warp pending
                                  (no exit accounting: an exited thread keeps the instance open)  ≠ A3
   memory access at pc            TV-completion-order: a pending warp issuing an access → reject;
                                  for each active lane t0 (address addr, loc):
                                    t ← t0;  if pc ∈ async_pcs: t ← agent(t0);
                                             own(t0); vc[t] ⊔= vc[t0]; own(t); (same on vs)   ≠ v3
                                    if pc ∈ atom_scope:                                   (RMW)
                                       append (t, atom_idx[t]++) to profile[addr]
                                       acquire: if released[loc] = (c, rb, rs) and
                                                (min(atom_scope[pc], rs) = GRID ∨ (= BLOCK ∧ rb = block)):
                                                vc[t] ⊔= c
                                       own(t); owns(t)
                                       w ← last_write[loc]: if w ∧ w.tid ≠ t ∧ ¬coherent(coh(pc), block, w.coh, w.block):
                                                Conflict(w, e) as "atomic"
                                       for r in last_reads[loc]: if r.tid ≠ t ∧ ¬coherent(...): Conflict(r, e) as "WAR"
                                       vc[t][t] ← own(t) + 1                     ← tick   ≠ v3 (v3: publish first)
                                       released[loc] ← (copy(vc[t]), block, atom_scope[pc])   ← publish (post-tick clock)
                                       last_write[loc] ← (t, vc[t][t], owns(t), pc, coh, block)  (post-tick epoch  ≠ v3)
                                       last_reads[loc] ← ∅
                                    else:                                          (read or write)
                                       ep ← own(t); sep ← owns(t)
                                       w ← last_write[loc]: if w ∧ ¬coherent(coh(pc), block, w.coh, w.block):
                                             if w.tid ≠ t: Conflict(w, e) as "WAW" | "RAW"
                                             else if write ∧ t is an agent: Conflict(w, e, observer = t0) as "WAW"   ≠ v3
                                       if write: for r in last_reads[loc]: if r.tid ≠ t ∧ ¬coherent(...): Conflict(r, e) as "WAR"
                                                 last_write[loc] ← (t, ep, sep, pc, coh, block);  last_reads[loc] ← ∅
                                       else:     last_reads[loc][t] ← (ep, sep, pc, coh, block)

Output: races deduplicated on (addr, a_tid, a_pc, b_tid, b_pc, kind), agent ids mapped back
to the issuing thread with "async" ∈ {a, b, ab};  races_sync_only = sync_pairs with counts;
coherence_profile = per-address (tid, index) sequences with their FNV-1a hash.
```

What section A has and this does not: exit records that retire threads from the barrier
count (v3 A3; T3b), publish-before-tick (T9/D1). What this has and section A does not:
the `coherent()` filter, the second clock and `races_sync_only`, the async agents with
commit/wait, the location-keyed release map, the TV monitor as runtime rejections.
