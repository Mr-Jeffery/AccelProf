"""A2-aware litmus criterion (T18; eval/A2_WINDOWS.md "Same source, two collectors").

The collector records an atomic at issue, so when two RMW windows on a location overlap,
trace order can invert coherence order (assumption A2) and the same program lands in
different schedules under different collector builds. Which report a schedule produces for a
lock idiom is then not a property of the program; whether the report is flagged is. The
criterion the litmus tests assert:

  * the reports that are NOT a2_uncertain must match the label (a race-free kernel has none;
    a labelled race keeps its labelled class, no extra unflagged DR beside a labelled SC);
  * every extra report must carry a2_uncertain with the flag equal to its count -- the verdict
    level flag (`v["a2_uncertain"] is True`) is exactly that: every instance of the pair's
    class is flagged (sync_dominance._a2_flag).

Scalar-clock mode has no hb_races and so no flags of its own; the flag of a pair is taken from
the vector-clock analysis of the same trace (`flagged_pairs`), because it is a property of the
trace's RMW windows, not of the mode.
"""


def _pair(v):
    return frozenset((v["current_pc"], v["ancient_pc"]))


def flagged_pairs(report):
    """pc pairs of a vector-clock report whose every instance is a2_uncertain."""
    return {_pair(v) for v in report["verdicts"] if v.get("a2_uncertain") is True}


def reports(report, flagged=None):
    """The reported verdicts (RACE, SC) of an analyze() report, as
    {"RACE": (unflagged, flagged), "SC": (unflagged, flagged)}; `flagged` is a pair set taken
    from the same trace's vector-clock analysis when `report` is a scalar-clock one."""
    flagged = flagged if flagged is not None else set()
    out = {"RACE": ([], []), "SC": ([], [])}
    for v in report["verdicts"]:
        if v["verdict"] in out:
            is_flagged = v.get("a2_uncertain") is True or _pair(v) in flagged
            out[v["verdict"]][1 if is_flagged else 0].append(v)
    return out


def counts(report, flagged=None):
    """(unflagged RACE, unflagged SC, flagged RACE, flagged SC) as counts."""
    r = reports(report, flagged)
    return (len(r["RACE"][0]), len(r["SC"][0]), len(r["RACE"][1]), len(r["SC"][1]))


def without_flag(mem):
    """T18: split the memory records (seq order, with "lanes") of a two-block litmus whose
    hand-off order is forced by a flag (testdata/write_after_unlock_other_schedule.cu,
    write_before_lock.cu: block 0 raises `go` with its LAST access, block 1 spins on it first).
    Returns (b0, b1, forced): both blocks' records without the flag's address, and whether the
    order is forced -- block 0's flag store precedes every non-flag record of block 1 (the
    windows of the two blocks' RMWs on the lock cannot overlap)."""
    b0 = [e for e in mem if e["block"] == 0]
    b1 = [e for e in mem if e["block"] == 1]
    if not b0 or not b1:
        return [], [], False
    flag = b0[-1]["lanes"][0]["addr"]
    on_flag = lambda e: e["lanes"][0]["addr"] == flag
    go = max(e["seq"] for e in b0 if on_flag(e))
    b0, b1 = [e for e in b0 if not on_flag(e)], [e for e in b1 if not on_flag(e)]
    return b0, b1, bool(b0 and b1) and go < b1[0]["seq"]
