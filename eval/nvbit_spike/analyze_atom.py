#!/usr/bin/env python3
"""T13 analyzer for atom_after records (eval/NVBIT_SPIKE.md, steps 3-4).

usage: analyze_atom.py PART RECORDS [APP_STDOUT]

Records ("AA K launch L seq S cta C tid T pc 0x.. op OP addr 0x.. val V"):
  M = BEFORE of a non-atomic memory instruction, B = BEFORE of an ATOM*,
  A = destination register at IPOINT_AFTER, N = the same read at the next
  instruction's IPOINT_BEFORE.  seq is one global atomicAdd counter.

An RMW is a B record paired with the next A/N record of the same thread and pc.
Its execution lies in (B.seq, A.seq).  Its Sanitizer-view window is
[B.seq, seq of the thread's next M/B record) -- the collector records every
memory access at issue, so an atomic's position in the trace is B.seq and it
executes somewhere before the thread's next record (A2 of hb_proof.tex).

Part 1/2/4 (atomicAdd counter): the value read is the RMW's coherence position
(scaled by the per-RMW increment).  Part 3 (lock): the lock word holds a tag
unique per critical section; the app prints the critical-section order
("ORDER t0 t1 ..."), so S_k (successful CAS, reads 0) and E_k (Exch, reads
tag_k) sit at coherence positions 2k and 2k+1, and a failed CAS reading tag_k
lies strictly between them (its order against other failed CASes of the same
k is not determined and never counted).
"""
import bisect
import collections
import json
import re
import sys

REC = re.compile(r"^AA (\w) launch (\d+) seq (\d+) cta (\d+) tid (\d+) pc 0x([0-9a-f]+) "
                 r"op (\S+) addr 0x([0-9a-f]+) val (\d+)")


def load(path):
    recs = []
    with open(path) as f:
        for line in f:
            m = REC.match(line)
            if m:
                k, L, s, c, t, pc, op, a, v = m.groups()
                recs.append(dict(kind=k, launch=int(L), seq=int(s), thr=(int(L), int(c), int(t)),
                                 pc=int(pc, 16), op=op, addr=int(a, 16), val=int(v)))
    recs.sort(key=lambda r: r["seq"])
    return recs


def rmws(recs):
    """Pair B with A/N; attach the Sanitizer-view window end."""
    by_thr = collections.defaultdict(list)
    for r in recs:
        by_thr[r["thr"]].append(r)
    out, unmatched_b, dropped_v = [], 0, 0
    for thr, rs in by_thr.items():
        pending = {}
        mem = [r for r in rs if r["kind"] in "MB"]
        mem_seqs = [r["seq"] for r in mem]
        for r in rs:
            if r["kind"] == "B":
                if r["pc"] in pending:
                    unmatched_b += 1
                pending[r["pc"]] = r
            elif r["kind"] in "AN":
                b = pending.pop(r["pc"], None)
                if b is None:
                    dropped_v += 1  # N record of a predicated-off atomic
                    continue
                i = bisect.bisect_right(mem_seqs, b["seq"])
                wend = mem_seqs[i] if i < len(mem_seqs) else float("inf")
                out.append(dict(thr=thr, pc=b["pc"], op=b["op"], addr=b["addr"], val=r["val"],
                                bseq=b["seq"], aseq=r["seq"], wend=wend))
        unmatched_b += len(pending)
    out.sort(key=lambda x: x["bseq"])
    return out, unmatched_b, dropped_v


def a2_stats(rs, pos, label):
    """rs sorted by bseq (trace order); pos[i] = coherence position (None =
    unknown).  Counts, over same-location RMW pairs of different warps:
    window-overlapping pairs, pairs inverted (coherence order opposite to
    trace order, only where determined), and inverted pairs whose windows do
    not overlap (A2's premise predicts 0)."""
    n = len(rs)
    warp = [(r["thr"][0], r["thr"][1], r["thr"][2] // 32) for r in rs]
    pairs = overl = inv = inv_overl = 0
    by_type = collections.Counter()
    sane_viol = 0
    for i in range(n):
        for j in range(i + 1, n):
            if warp[i] == warp[j]:
                continue
            pairs += 1
            o = rs[j]["bseq"] < rs[i]["wend"]  # j issued inside i's window
            overl += o
            if pos[i] is None or pos[j] is None:
                continue
            if pos[j] < pos[i]:
                inv += 1
                inv_overl += o
                by_type[(label(i), label(j))] += 1
            # execution intervals must respect coherence order
            first, second = (i, j) if pos[i] < pos[j] else (j, i)
            if pos[i] != pos[j] and not rs[first]["bseq"] < rs[second]["aseq"]:
                sane_viol += 1
    return dict(rmws=n, pairs=pairs, overlapping=overl, inverted=inv,
                inverted_overlapping=inv_overl, inverted_nonoverlapping=inv - inv_overl,
                inverted_by_type={f"{a}<trace {b}": c for (a, b), c in sorted(by_type.items())},
                exec_interval_violations=sane_viol)


def counter_part(part, rs):
    vals = [r["val"] for r in rs]
    res = dict(part=part, rmws=len(rs), values_sorted_by_trace=vals if len(vals) <= 16 else None)
    if part == 1:
        res["ok"] = vals == list(range(8))
    elif part == 2:
        res["ok"] = sorted(vals) == list(range(0, 256, 32))
    elif part == 4:
        res["ok"] = sorted(vals) == list(range(256))
    res.update(a2_stats(rs, vals, lambda i: "ADD"))
    return res


def lock_part(rs, order):
    k_of = {t: k for k, t in enumerate(order)}
    locks = collections.Counter(r["addr"] for r in rs if r["op"].startswith("ATOMG.E.CAS"))
    lock_addr = locks.most_common(1)[0][0]
    rs = [r for r in rs if r["addr"] == lock_addr]
    errors = []
    pos, kind = [], []
    # E_k: Exch reads tag_k. S_k: that thread's last CAS before E_k (reads 0).
    by_thr = collections.defaultdict(list)
    for idx, r in enumerate(rs):
        by_thr[r["thr"]].append(idx)
    p = [None] * len(rs)
    kd = ["?"] * len(rs)
    for thr, ids in by_thr.items():
        for n_, idx in enumerate(ids):
            r = rs[idx]
            if "EXCH" in r["op"]:
                if r["val"] not in k_of:
                    errors.append(f"Exch read {r['val']} (not a tag)")
                    continue
                k = k_of[r["val"]]
                p[idx], kd[idx] = 2 * k + 1, "E"
                prev = ids[n_ - 1] if n_ else None
                if prev is None or "CAS" not in rs[prev]["op"] or rs[prev]["val"] != 0:
                    errors.append(f"E_{k} not preceded by a successful CAS of its thread")
                else:
                    p[prev], kd[prev] = 2 * k, "S"
            elif "CAS" in r["op"] and r["val"] != 0:
                if r["val"] not in k_of:
                    errors.append(f"failed CAS read {r['val']} (not a tag)")
                    continue
                p[idx], kd[idx] = 2 * k_of[r["val"]] + 0.5, "F"
    for idx, r in enumerate(rs):
        if "CAS" in r["op"] and r["val"] == 0 and kd[idx] != "S":
            errors.append("successful CAS without a matching Exch")
    # alternation: S_0 E_0 S_1 E_1 ... all present
    seen = sorted(x for x in p if x is not None and x == int(x))
    alternation_ok = seen == list(range(2 * len(order)))
    st = a2_stats(rs, p, lambda i: kd[i])
    # the T9 shape: S_{k+1} recorded before E_k, the unlock it read from
    e_seq = {p[i] // 2: rs[i]["bseq"] for i in range(len(rs)) if kd[i] == "E"}
    s_before_release = sum(1 for i in range(len(rs)) if kd[i] == "S" and p[i] // 2 >= 1
                           and rs[i]["bseq"] < e_seq.get(p[i] // 2 - 1, -1))
    return dict(part=3, lock_rmws=len(rs), cas_success=kd.count("S"), cas_fail=kd.count("F"),
                exch=kd.count("E"), critical_sections=len(order), alternation_ok=alternation_ok,
                value_errors=errors[:10], n_value_errors=len(errors),
                success_recorded_before_release_read=s_before_release, **st)


def main():
    part, path = int(sys.argv[1]), sys.argv[2]
    recs = load(path)
    rs, ub, dv = rmws(recs)
    base = dict(records=len(recs), unmatched_before=ub, dropped_values=dv)
    if part == 3:
        order = None
        for line in open(sys.argv[3]):
            if line.startswith("ORDER"):
                order = [int(x) for x in line.split()[1:]]
        res = lock_part(rs, order)
    else:
        res = counter_part(part, rs)
    res.update(base)
    print(json.dumps(res))


if __name__ == "__main__":
    main()
