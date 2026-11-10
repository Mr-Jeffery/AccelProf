"""X13: the per-kernel fold, one level below X10's per-binary fold (make_tables.fold_verdict / fold_binaries).

Unit: one kernel = one __global__ function of one binary. For one binary and one (tool, mode), `runs` is a list of
run dicts (one per manifest id of the binary):
    verdict   : the run's own verdict, RACE / CLEAN / TIMEOUT / ERROR (X10's per-run value)
    launched  : set of kernel names with at least one finished launch in this run
    reporting : set of kernel names a report of this run is attributed to
Rule (Jeffery, 2026-11-07), per kernel k of `universe` (the kernels some run of the binary launched):
    RACE     if any run has a report attributed to k;
    CLEAN    if every run has at least one finished launch of k and none reports;
    TIMEOUT  if some run has no finished launch of k, no report, and some such run is a TIMEOUT run;
    ERROR    otherwise.
A kernel of the cubin that no run launched is not in `universe` and is not counted."""
from collections import defaultdict


def fold_kernel(k, runs):
    if any(k in r["reporting"] for r in runs):
        return "RACE"
    missing = [r for r in runs if k not in r["launched"]]
    if not missing:
        return "CLEAN"
    return "TIMEOUT" if any(r["verdict"] == "TIMEOUT" for r in missing) else "ERROR"


def universe_of(all_runs):
    """Kernels launched by some run (any tool/mode that carries launches)."""
    u = set()
    for r in all_runs:
        u |= set(r["launched"])
    return u


def fold_kernels(runs, universe):
    return {k: fold_kernel(k, runs) for k in sorted(universe)}


def fold_back(kernel_verdicts):
    """The binary verdict implied by its kernel verdicts, X10's rule one level up: RACE if any kernel RACE; CLEAN if
    all CLEAN; TIMEOUT if some TIMEOUT; otherwise ERROR."""
    vs = list(kernel_verdicts.values())
    if not vs:
        return None
    if "RACE" in vs:
        return "RACE"
    if all(v == "CLEAN" for v in vs):
        return "CLEAN"
    return "TIMEOUT" if "TIMEOUT" in vs else "ERROR"


def confusion_k(kernels, labels, verdicts):
    """kernels: [(binary, kernel)]; labels[(binary, kernel)] in RACE/CLEAN/''; verdicts[(binary, kernel)] -> verdict or None
    (tool did not run). Same cell semantics as make_tables.confusion_b."""
    c = dict(tp=0, fn=0, fp=0, tn=0, to=0, err=0, unl=0, n=0, lab_r=0, lab_c=0)
    for bk in kernels:
        v = verdicts.get(bk)
        if v is None:
            continue
        lab = labels.get(bk, "")
        c["n"] += 1
        c["lab_r"] += lab == "RACE"
        c["lab_c"] += lab == "CLEAN"
        if v == "TIMEOUT":
            c["to"] += 1
        elif v == "ERROR":
            c["err"] += 1
        elif lab == "RACE":
            c["tp" if v == "RACE" else "fn"] += 1
        elif lab == "CLEAN":
            c["fp" if v == "RACE" else "tn"] += 1
        else:
            c["unl"] += 1
    assert sum(c[x] for x in ("tp", "fn", "fp", "tn", "to", "err", "unl")) == c["n"]
    return c
