# design/proof — inputs for task T6 (pseudo-code as implemented) and T9 (soundness)

Placed here on 2026-09-24 from the cuRace project documents (both dated 2026-09-15).
`docs/` in this repo is the upstream documentation submodule, so the proof material and
the T6/T9 deliverables live under `design/`, next to `design/host_memcpy_model.md`.

| file | what it is | status |
|---|---|---|
| `hb_oracle_proof_v3.tex` | The reference: trace model (memory, arrival, **exit** records; ghost arrival/departure events), well-formedness W0–W2 and the monitor, **Algorithm 1** (`alg:hb`), the clock invariant, the two single-trace theorems, the per-profile certificate, §"State of the implementation". | Authoritative for what `hb_oracle.py` / `HbEngine` are measured against. |
| `hb_defs_v4.tex` | Revision-4 delta: strength/scope labels, the two verdicts DR / SC (PTX §8.7.1), fence-gated (ATOM) via static fence adjacency (`rel`/`acq`), release chains, per-class **buckets** replacing FastTrack last-write/readers, the four-step processing rule (Definition "Processing a record"), obligations O1–O6. | The newest algorithm. A proposal: its four modelling decisions are still Jeffery's to confirm; nothing of it is implemented. |
| `algorithm1_reference.md` | Plain-text rendering of Algorithm 1 as the progress deck states it (same content as `alg:hb`), the v4 processing rule in the same style, and the record kinds the code has added since (async agents). | Convenience copy; the `.tex` files win on any discrepancy. |

Terminology (v3 §Terminology, v4 keeps it): **sound** = misses no race / no missed
verdict; **complete** = every report is a race / no spurious verdict.
Theorem `thm:sound` is location-level soundness, `thm:complete` completeness.

A companion PC-level document (`hb_pc_level_v4.tex`, scalar-clock mode) is referenced in
the project notes but is not among the project documents; if it exists, add it here.

## Seed for T6's deviation table — code at `cuVein` 3331d35 (2026-09-23) vs Algorithm 1

Each line is a place where what runs differs from `alg:hb`, with where to look. T6
confirms, extends and files each one as *proof right / code right / decision needed*.

1. **Tick before publish.** `alg:hb` publishes `lastRelease[x] ← clock[t]` and records
   the atomic at the pre-tick epoch, *then* ticks. `python/hb_oracle.py` (atomic branch)
   and `HbEngine::process` do the opposite (`vc[t][t] = own(t)+1`, then
   `released[loc] = vc[t]`), so the published clock covers the releaser's post-release
   accesses. Consequence and the fix are T9 Part 3 (decision D1). The deck's Algorithm 1
   slide says "publish, then tick" and notes the discrepancy.
2. **Exit records.** v3 has exit records in the trace model, "exit: do nothing" in the
   algorithm, and puts the barrier count on the collector through A3 ("a thread that
   exits is not among [the threads the hardware barrier waits for]"). The collector emits
   `BlockExit` records but `hb_collect_events` drops them from `hb_events`, and
   `exp(A)` is `thread_count` or `block_thread_count` with no exit accounting. T3
   (2026-09-23) showed the effect on HeCBench `crs-cuda`: threads that return before a
   `__syncthreads()` never arrive, the instance never completes, every
   store → barrier → load pair stays unordered (155 / 7 spurious reports; the program is
   race-free). Proposed fix: exit-aware expected count in `HbEngine`, `hb_oracle.py` and
   `barrier_only_pairs` (strict xfails in `python/test_barrier_exit.py`). For the proof:
   either A3 is discharged by the collector (count from hardware) or Definition
   "Expected count" must subtract exited threads — T6 states which, T3b implements.
3. **cp.async copies (T1a, merged 2026-09-23).** New record kinds `pipeline_commit` /
   `pipeline_wait`, and an LDGSTS copy is a write by the issuing thread's *async agent*
   (`tid | 1<<62`), ordered after the thread's earlier accesses; each `commit_group`
   snapshots the agent's clock (the agent ticks at commit), `wait_group N` joins the
   snapshot of the newest group it completes. Same model in `HbEngine`, `hb_oracle.py`,
   `barrier_only_pairs`. Not in v3's trace model: T6 writes the extension (new events,
   their PO placement, the two new HB generators) so that T9 can check the theorems still
   hold. Review follow-up (3331d35): the static rules give no R1/R2 credit when the
   earlier access is a copy and no R3 credit to a pair with a copy; two copies of one
   thread to one location are checked against the issuing thread's view of its agent;
   copies completed through an mbarrier (`ARRIVES.LDGSTSBAR`) keep the pre-T1a reading
   until T1b; `--assume-warp-lockstep` never orders a record involving a copy.
4. **Conflict filter `coherent()`** (`coherent_scope`, policy `--strong-ldst`, RC1 fix):
   `.STRONG` loads/stores are treated as coherent for the pairwise conflict test only —
   they join no clocks. v3's Definition "Conflict" has no such filter; v4's DR/SC split
   is the principled version. Record as "v4 direction, partial".
5. **RMW-vs-readers check**: the atomic branch now also checks `last_reads` (v3's
   `Check` already does this for atomics — confirm the code matches `Check`).
6. **Release map keyed by location** (F6) — matches v3 (`lastR[x]` per address; shared
   memory is per block in `loc`). **Reader pcs in WAR records** (F2) — matches
   `readers[ℓ]` holding `(epoch, pc)`.
7. **Second, barrier-only clock** (`vs`, `hb_races_sync_only`; offline
   `barrier_only_pairs`) — not in v3; it is the verdict matrix's `barrier-ordered` /
   `latent` input. Needs its own statement (it is v4's `HB^+`-style second instance with
   (ATOM) removed rather than unlocked).
8. **Monitor parity** (v3 §"State of the implementation" item 1): per-warp join when the
   expected count is unknown; no consistency check of `exp` along a key.
9. **Local memory** keyed by `(space, addr)` in the code, per thread in v3 (item 5).
10. **Fence-gated (ATOM)** (v3 item 4, v4 Definition "Fence adjacency") — open,
    corpus-affecting; every strong RMW is release/acquire in the code
    (`test_relaxed_handoff_should_race` is the strict xfail).
11. **Host operations (T2, flag `YOSEMITE_HB_HOST_MEMCPY`)** — `python/host_hb.py`
    orders streams, events and host synchronisation outside the kernel trace model;
    off by default; outside both documents.
12. **Observational additions** — coherence profile Π and its hash, TV invariants as
    runtime checks (v3 Definition "Well-formedness monitor"), `YOSEMITE_HB_STATS`.

Scalar-clock mode (R1 dominance, R2 coherence, R3 chain with the CAS past-release gate,
the offline barrier-only pass, event-stream candidates, edge rescue, the verdict matrix)
has no proof document here; T6's Algorithm 2 is its first precise statement.
