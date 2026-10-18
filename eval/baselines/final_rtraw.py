#!/usr/bin/env python3
"""X4 (the rtraw case study; report eval/FINAL_RTRAW.md): record the ScoR litmus
race_interblock_none-lock_rtraw and the forced-order kernel
python/testdata/write_after_unlock_other_schedule.cu, then read every run's dump.

  record   (GPU node) N recordings of one binary with the harness's environment
           (blib.base_env: YOSEMITE_HB_TRACE=1, YOSEMITE_HB_MODE=<mode>, the atomic-scope sidecar,
           $BASELINE_HB_DUMP=1 -> the lossless dump), plus YOSEMITE_HB_STATS=0 and, with --policy,
           YOSEMITE_HB_GATE_POLICY; every other YOSEMITE_* / CUVEIN_* variable is removed from the
           environment first. `accelprof -t pc_dependency_analysis -n 1 ./<binary>` as
           parallel.py runs it. Layout: <store>/<label>/<node>/cfg/ (dots, sidecar, built binary),
           <store>/<label>/<node>/run<k>/{kernel_0.json, meta.json, accelprof.err}.
  analyze  (any node) per run: the acquisition order read from the lock word's RMW records, the
           windows of the hand-off, the rtraw pair (block 0's write after its unlock, block 1's
           read of the same word) with its verdict, class and a2_uncertain flag from
           sync_dominance.analyze (the aggregates path, X0) and from the record replay
           (CUVEIN_PREFER_RECORDS=1), HbClock == hb_oracle (records, sync-only pairs, chain), and
           for recordings under the recorded policy a replay of the SAME trace under the certain
           policy (hb_oracle --gate-policy certain, hb_races swapped in as t16_rescore.py does).
           Writes <out>/runs.csv and <out>/runs.json.
  tables   runs.json -> <out>/runs_summary.md (per label and node: runs by acquisition order,
           distinct schedules, the pair's verdicts, the checks).

    W=<worktree> sbatch -w <node> eval/baselines/setup/p_final_rtraw.sh      (recordings)
    .env/bin/python eval/baselines/final_rtraw.py analyze eval/results/final-rtraw
    .env/bin/python eval/baselines/final_rtraw.py tables  eval/results/final-rtraw
"""
import argparse
import copy
import csv
import glob
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
WT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, f"{WT}/python")
sys.path.insert(0, HERE)

KNOB_PREFIXES = ("YOSEMITE_", "CUVEIN_")
KEEP_VARS = ("CUVEIN_HOME",)


def _sha16(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def _sh(cmd, env=None):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, env=env,
                              timeout=60).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


# ---------------------------------------------------------------- record

def cmd_record(a):
    # no inherited knob: only what base_env sets, YOSEMITE_HB_STATS=0 and the policy
    for k in list(os.environ):
        if k.startswith(KNOB_PREFIXES) and k not in KEEP_VARS:
            del os.environ[k]
    os.environ["BASELINE_HB_DUMP"] = "1"
    import blib
    cuda = blib.resolve_cuda_home()
    env0 = blib.base_env(cuda)
    node = socket.gethostname()
    root = f"{a.store}/{a.label}/{node}"
    cfg = f"{root}/cfg"
    os.makedirs(root, exist_ok=True)
    if a.src:
        # built exactly as test_hb_substitutions._trace builds it
        os.makedirs(cfg, exist_ok=True)
        exe = f"{cfg}/{Path(a.src).stem}"
        b = subprocess.run(["nvcc", "-arch=native", "-lineinfo", "--cudart", "shared",
                            a.src, "-o", exe], capture_output=True, text=True, env=env0)
        if b.returncode != 0:
            sys.exit(f"build failed: {b.stderr[-600:]}")
        build = f"nvcc -arch=native -lineinfo --cudart shared {a.src}"
    else:
        exe = os.path.realpath(a.exe)
        build = "prebuilt"
    scope, cubs = blib.extract(exe, f"{cfg}/cubins", env0)
    for dot in glob.glob(f"{cfg}/cubins/*.dot"):
        shutil.copy(dot, cfg)
    if scope:
        shutil.copy(scope, f"{cfg}/atomic_scope.txt")
    scope = f"{cfg}/atomic_scope.txt" if scope else None
    shutil.rmtree(f"{cfg}/cubins", ignore_errors=True)
    aph = blib.APH
    gpu = _sh(["nvidia-smi", "--query-gpu=name,compute_cap,driver_version",
               "--format=csv,noheader"], env0)
    cpu = next((ln.split(":", 1)[1].strip() for ln in _sh(["lscpu"]).splitlines()
                if ln.startswith("Model name")), "?")
    common = dict(
        node=node, gpu=gpu, cpu=cpu, cuda_home=cuda,
        nvcc=_sh([f"{cuda}/bin/nvcc", "--version"]).splitlines()[-1:] or [""],
        accel_prof_home=aph, exe=exe, exe_sha16=_sha16(exe), build=build,
        source=a.src or a.exe, label=a.label, mode=a.mode, policy=a.policy or "recorded",
        runtime=dict(libsanalyzer=_sha16(f"{aph}/build/sanalyzer/lib/libsanalyzer.so"),
                     collector=_sha16(f"{aph}/lib/libcompute_sanitizer.so"),
                     fatbin=_sha16(f"{aph}/nv-compute/lib/gpu_patch/"
                                   "gpu_patch_pc_dependency.fatbin")),
        slurm_job=os.environ.get("SLURM_JOB_ID", ""))
    Path(f"{root}/node.json").write_text(json.dumps(common, indent=1))
    base = os.path.basename(exe)
    for k in range(1, a.runs + 1):
        rd = f"{root}/run{k}"
        shutil.rmtree(rd, ignore_errors=True)
        os.makedirs(rd)
        os.symlink(exe, f"{rd}/{base}")
        env = blib.base_env(cuda, hb_trace=True, hb_mode=a.mode, scope_file=scope)
        env["YOSEMITE_HB_STATS"] = "0"
        if a.policy:
            env["YOSEMITE_HB_GATE_POLICY"] = a.policy
        knobs = {k_: v for k_, v in env.items() if k_.startswith(KNOB_PREFIXES)}
        cmd = ["accelprof", "-t", "pc_dependency_analysis", "-n", "1", f"./{base}"]
        started = time.strftime("%Y-%m-%d %H:%M:%S")
        wall, _peak, rc, to = blib.run_timed(cmd, env, rd, a.timeout,
                                             stderr_path=f"{rd}/accelprof.err")
        deps = sorted(glob.glob(f"{rd}/dependency_{base}_*"), key=os.path.getmtime)
        kjs = sorted(glob.glob(f"{deps[-1]}/kernel_*.json")) if deps else []
        for kj in kjs:
            shutil.move(kj, f"{rd}/{os.path.basename(kj)}")
        for d in deps:
            shutil.rmtree(d, ignore_errors=True)
        os.unlink(f"{rd}/{base}")
        meta = dict(run=k, started=started, wall=wall, rc=rc, timed_out=to,
                    kernels=[os.path.basename(x) for x in kjs], knobs=knobs,
                    command=" ".join(cmd))
        Path(f"{rd}/meta.json").write_text(json.dumps(meta, indent=1))
        print(f"{node} {a.label} run{k}: rc={rc} timed_out={to} wall={wall} "
              f"kernels={len(kjs)}", flush=True)


# ---------------------------------------------------------------- analyze

def _addr(e):
    return e["lanes"][0]["addr"]


def _block(mem, lock):
    """One block's records (seq order): its CAS attempts on the lock word (the records on the
    lock before its first other record), its unlock (the last lock record), the critical section
    between, and what follows the unlock."""
    first_other = next(e for e in mem if _addr(e) != lock)
    cas = [e for e in mem if _addr(e) == lock and e["seq"] < first_other["seq"]]
    unlock = [e for e in mem if _addr(e) == lock][-1]
    crit = [e for e in mem if cas[-1]["seq"] < e["seq"] < unlock["seq"]]
    post = [e for e in mem if e["seq"] > unlock["seq"]]
    return dict(cas=cas, succ=cas[-1], unlock=unlock, crit=crit, post=post)


def _next_seq(events, e):
    """Seq of the next record (any type, exits included) of e's thread: the end of e's window."""
    nxt = [x["seq"] for x in events if x["block"] == e["block"] and x["warp"] == e["warp"]
           and x["seq"] > e["seq"]]
    return min(nxt) if nxt else None


def _verdict(dots, trace_path):
    import sync_dominance as sd
    for dot in dots:
        try:
            return dot, sd.analyze(dot, trace_path)
        except sd.AlignmentError:
            continue
    raise RuntimeError(f"no CFG aligns with {trace_path}")


PAPER = {"structural": "Race", "sc": "Strong conflict", "latent": "Latent",
         "latent-sc": "Latent (SC)", "ordered": "Ordered", "barrier-ordered": "Ordered",
         None: "-"}


def _pair(rep, pcs):
    vs = [v for v in rep["verdicts"] if {v["current_pc"], v["ancient_pc"]} == set(pcs)]
    if not vs:
        return dict(verdict="none", hb_class=None, paper="not a candidate")
    v = vs[0]
    return dict(verdict=v["verdict"], hb_class=v["hb_class"], paper=PAPER.get(v["hb_class"], "?"),
                conflict_class=v.get("conflict_class"), race_type=v["race_type"],
                a2_uncertain=v.get("a2_uncertain"), model_bug=v.get("model_bug"),
                event_candidate=v.get("event_candidate"), hb_chain=v.get("hb_chain"))


def _others(rep, pcs):
    return [f"{v['ancient_pc']:#x}->{v['current_pc']:#x} {v['race_type']} {v['hb_class']} "
            f"a2={v.get('a2_uncertain')}"
            for v in rep["verdicts"] if v["verdict"] != "ORDERED"
            and {v["current_pc"], v["ancient_pc"]} != set(pcs)]


def _program(rep):
    """The program-level reading of run_cuvein._analyze_reports: RACE iff some pair's verdict
    is RACE (a structural or latent DR, the Race u Latent point; Race alone drops latent), and
    the number of SC reports beside it (sc, latent-sc: informational under PTX, D2)."""
    race = [v["hb_class"] for v in rep["verdicts"] if v["verdict"] == "RACE"]
    return dict(race_u_latent="RACE" if race else "CLEAN",
                race_alone="RACE" if any(c != "latent" for c in race) else "CLEAN",
                sc_reports=sum(v["verdict"] == "SC" for v in rep["verdicts"]))


def _race_key(r):
    return (r.get("a_pc"), r["b_pc"], r["kind"], r.get("class"), r["space"], r.get("dist"),
            r.get("async"), r.get("count"), r.get("a2_uncertain"))


def analyze_run(rd, dots, forced_kernel):
    import a2_aware
    import hb_oracle
    kp = f"{rd}/kernel_0.json"
    t = json.loads(Path(kp).read_text())
    meta = json.loads(Path(f"{rd}/meta.json").read_text())
    ev = sorted(t["hb_events"], key=lambda e: e["seq"])
    mem = [e for e in ev if "lanes" in e]
    row = dict(run=meta["run"], rc=meta["rc"], timed_out=meta["timed_out"], events=len(ev),
               mode=meta["knobs"].get("YOSEMITE_HB_MODE"),
               policy=meta["knobs"].get("YOSEMITE_HB_GATE_POLICY", "recorded"),
               dump_policy=t.get("hb_gate_policy"), tv=t.get("tv_violation"),
               chain=t.get("hb_chain"))
    if forced_kernel:
        b0m, b1m, forced = a2_aware.without_flag(mem)
        row["forced"] = forced
    else:
        b0m = [e for e in mem if e["block"] == 0]
        b1m = [e for e in mem if e["block"] == 1]
    lock = _addr(b0m[0])
    assert _addr(b1m[0]) == lock, "both blocks must start on the lock word"
    blk = {0: _block(b0m, lock), 1: _block(b1m, lock)}
    write = blk[0]["post"][0]
    assert write["type"] == "write", write
    data = _addr(write)
    read = next(e for e in blk[1]["crit"] if e["type"] == "read" and _addr(e) == data)
    first = 0 if blk[0]["succ"]["seq"] < blk[1]["succ"]["seq"] else 1
    second = 1 - first
    first_crit = 0 if blk[0]["crit"][0]["seq"] < blk[1]["crit"][0]["seq"] else 1
    # the hand-off: the first owner's unlock and the next RMW on the lock word in trace order
    lock_rmws = [e for e in mem if _addr(e) == lock]
    un = blk[first]["unlock"]
    after = [e for e in lock_rmws if e["seq"] > un["seq"]]
    un_end = _next_seq(ev, un)
    succ2 = blk[second]["succ"]
    row.update(
        first_acquirer=f"block {first}", first_by_critical_section=f"block {first_crit}",
        cas_attempts_b0=len(blk[0]["cas"]), cas_attempts_b1=len(blk[1]["cas"]),
        cas_seqs_b0=" ".join(str(e["seq"]) for e in blk[0]["cas"]),
        cas_seqs_b1=" ".join(str(e["seq"]) for e in blk[1]["cas"]),
        succ_cas_b0=blk[0]["succ"]["seq"], succ_cas_b1=blk[1]["succ"]["seq"],
        unlock_b0=blk[0]["unlock"]["seq"], unlock_b1=blk[1]["unlock"]["seq"],
        handoff_unlock=un["seq"], handoff_unlock_window_end=un_end,
        handoff_next_rmw=after[0]["seq"] if after else None,
        handoff_next_rmw_block=after[0]["block"] if after else None,
        handoff_overlap=bool(after and un_end is not None and after[0]["seq"] < un_end),
        succ_cas_before_unlock=succ2["seq"] < un["seq"],   # A2: a CAS recorded before what it read
        lock_rmws=" ".join(f"b{e['block']}:{e['pc']:#x}@{e['seq']}[..{_next_seq(ev, e)})"
                           for e in lock_rmws),
        read_seq=read["seq"], read_pc=read["pc"], write_seq=write["seq"], write_pc=write["pc"])
    pcs = (write["pc"], read["pc"])
    pair_recs = [r for r in t.get("hb_races") or ()
                 if {r.get("a_pc"), r["b_pc"]} == set(pcs)]
    row["pair_hb_races"] = [dict(kind=r["kind"], cls=r.get("class"), count=r.get("count"),
                                 a2_uncertain=r.get("a2_uncertain")) for r in pair_recs]
    row["hb_races_total"] = len(t.get("hb_races") or ())
    os.environ.pop("CUVEIN_PREFER_RECORDS", None)
    dot, rep = _verdict(dots, kp)
    row["pair"] = _pair(rep, pcs)
    row["others"] = _others(rep, pcs)
    row["program"] = _program(rep)
    os.environ["CUVEIN_PREFER_RECORDS"] = "1"
    _d, rep_r = _verdict(dots, kp)
    os.environ.pop("CUVEIN_PREFER_RECORDS", None)
    row["records_path_same"] = (_pair(rep_r, pcs) == row["pair"]
                                and _others(rep_r, pcs) == row["others"])
    if "hb_races" in t:
        orc = hb_oracle.analyze(dot, kp, records=True)
        row["hbclock_eq_oracle"] = (
            {_race_key(r) for r in t["hb_races"]} == {_race_key(r) for r in orc["races"]}
            and t.get("hb_races_sync_only") == orc["races_sync_only"]
            and t.get("hb_chain") == orc.get("chain"))
        if row["policy"] == "recorded":
            # the same trace under the certain clock (offline; t16_rescore.py's swap)
            orc_c = hb_oracle.analyze(dot, kp, gate_policy="certain")
            tc = copy.deepcopy(t)
            tc["hb_races"] = orc_c["races"]
            tc["hb_races_sync_only"] = orc_c["races_sync_only"]
            tc["hb_gate_policy"] = "certain"
            tc["hb_chain"] = orc_c.get("chain")
            with tempfile.TemporaryDirectory() as td:
                p = f"{td}/kernel_0.json"
                Path(p).write_text(json.dumps(tc))
                _d, rep_c = _verdict(dots, p)
            row["replay_certain_chain"] = orc_c.get("chain")
            row["replay_certain_pair"] = _pair(rep_c, pcs)
            row["replay_certain_others"] = _others(rep_c, pcs)
            row["replay_certain_program"] = _program(rep_c)
    return row


CSV_COLS = ["label", "node", "run", "mode", "policy", "rc", "events", "first_acquirer",
            "first_by_critical_section", "cas_attempts_b0", "cas_attempts_b1", "succ_cas_b0",
            "succ_cas_b1", "unlock_b0", "unlock_b1", "handoff_unlock",
            "handoff_unlock_window_end", "handoff_next_rmw", "handoff_overlap",
            "succ_cas_before_unlock", "read_pc", "read_seq", "write_pc", "write_seq",
            "pair_verdict", "pair_class", "pair_paper", "pair_conflict", "pair_kind",
            "pair_a2_uncertain", "pair_hb_races", "others", "program_race_alone",
            "program_race_u_latent", "program_sc_reports", "records_path_same",
            "hbclock_eq_oracle", "certain_replay_pair", "certain_replay_others",
            "certain_replay_program", "tv", "chain", "lock_rmws"]


def cmd_analyze(a):
    rows = []
    for nodedir in sorted(glob.glob(f"{a.root}/*/*/node.json")):
        nd = os.path.dirname(nodedir)
        common = json.loads(Path(nodedir).read_text())
        dots = sorted(glob.glob(f"{nd}/cfg/*.dot"))
        forced = "write_after_unlock" in common["source"]
        for rd in sorted(glob.glob(f"{nd}/run*"), key=lambda p: int(p.rsplit("run", 1)[1])):
            if not os.path.exists(f"{rd}/kernel_0.json"):
                rows.append(dict(label=common["label"], node=common["node"],
                                 run=int(rd.rsplit("run", 1)[1]), error="no kernel json"))
                continue
            r = analyze_run(rd, dots, forced)
            r.update(label=common["label"], node=common["node"])
            rows.append(r)
            print(f"{r['label']} {r['node']} run{r['run']}: first={r.get('first_acquirer')} "
                  f"pair={r['pair']['paper']} ({r['pair'].get('hb_class')}, "
                  f"a2={r['pair'].get('a2_uncertain')}) "
                  f"certain-replay={r.get('replay_certain_pair', {}).get('paper')}", flush=True)
    Path(f"{a.root}/runs.json").write_text(json.dumps(rows, indent=1, default=str))
    with open(f"{a.root}/runs.csv", "w", newline="") as f:
        w = csv.DictWriter(f, CSV_COLS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            if "error" in r:
                w.writerow({k: r.get(k) for k in ("label", "node", "run")})
                continue
            p, c = r["pair"], r.get("replay_certain_pair") or {}
            w.writerow(dict(
                r, read_pc=f"{r['read_pc']:#x}", write_pc=f"{r['write_pc']:#x}",
                pair_verdict=p["verdict"], pair_class=p.get("hb_class"), pair_paper=p["paper"],
                pair_conflict=p.get("conflict_class"), pair_kind=p.get("race_type"),
                pair_a2_uncertain=p.get("a2_uncertain"),
                pair_hb_races=json.dumps(r["pair_hb_races"]), others=" | ".join(r["others"]),
                program_race_alone=r["program"]["race_alone"],
                program_race_u_latent=r["program"]["race_u_latent"],
                program_sc_reports=r["program"]["sc_reports"],
                certain_replay_pair=c.get("paper", ""),
                certain_replay_others=" | ".join(r.get("replay_certain_others", [])),
                certain_replay_program=json.dumps(r.get("replay_certain_program")) if c else "",
                chain=json.dumps(r.get("chain"))))
    print(f"{len(rows)} runs -> {a.root}/runs.csv")


def _sig(r):
    """A run's schedule: the lock word's RMW records (block, pc, seq, window end) and the seqs
    of the pair's read and write."""
    return f"{r['lock_rmws']} | read@{r['read_seq']} write@{r['write_seq']}"


def cmd_tables(a):
    """runs.json -> runs_summary.md: per label and node, the runs by acquisition order, the
    distinct schedules, the pair's verdicts, and the checks."""
    from collections import Counter, OrderedDict
    rows = json.loads(Path(f"{a.root}/runs.json").read_text())
    out = ["# X4 recordings: summary (generated by `final_rtraw.py tables`)", ""]
    labels = OrderedDict((r["label"], 1) for r in rows)
    for lab in labels:
        rs = [r for r in rows if r["label"] == lab]
        bad = [r for r in rs if "error" in r or r.get("rc") != 0 or r.get("timed_out")]
        out += [f"## {lab}: {len(rs)} runs ({len(bad)} failed)", "",
                "| node | runs | block 0 first | block 1 first | crit-section order agrees | "
                "A2: winning CAS before the unlock | hand-off windows overlap | distinct schedules |",
                "|---|---|---|---|---|---|---|---|"]
        nodes = OrderedDict((r["node"], 1) for r in rs)
        for nd in list(nodes) + ["all"]:
            sub = [r for r in rs if (nd == "all" or r["node"] == nd) and "error" not in r]
            b0 = sum(r["first_acquirer"] == "block 0" for r in sub)
            agree = sum(r["first_acquirer"] == r["first_by_critical_section"] for r in sub)
            inv = sum(bool(r["succ_cas_before_unlock"]) for r in sub)
            ov = sum(bool(r["handoff_overlap"]) for r in sub)
            out.append(f"| {nd} | {len(sub)} | {b0} | {len(sub) - b0} | {agree}/{len(sub)} | "
                       f"{inv} | {ov} | {len(Counter(_sig(r) for r in sub))} |")
        ok = [r for r in rs if "error" not in r]
        out += ["", "Pair verdicts (verdict, class, paper term, a2_uncertain, hb_races of the pair):", ""]
        for k, n in Counter((r["pair"]["verdict"], r["pair"].get("hb_class"), r["pair"]["paper"],
                             r["pair"].get("a2_uncertain"), json.dumps(r["pair_hb_races"]))
                            for r in ok).most_common():
            out.append(f"- {n} x {k}")
        oth = Counter(" | ".join(r["others"]) or "(none)" for r in ok)
        out += ["", "Other non-ORDERED pairs: " + "; ".join(f"{n} x {k}" for k, n in oth.items())]
        prog = Counter((r["program"]["race_alone"], r["program"]["race_u_latent"],
                        r["program"]["sc_reports"]) for r in ok)
        out += ["", "Program verdict (Race alone, Race u Latent, SC reports): "
                + "; ".join(f"{n} x {k}" for k, n in prog.most_common())]
        if any("replay_certain_pair" in r for r in ok):
            cp = Counter((r["replay_certain_pair"]["paper"],
                          r["replay_certain_pair"].get("a2_uncertain"),
                          " | ".join(r["replay_certain_others"]) or "(none)",
                          json.dumps(r["replay_certain_chain"]),
                          json.dumps(r["replay_certain_program"])) for r in ok)
            out += ["", "Same trace replayed under the certain clock (pair, a2, other reports, "
                    "chain, program):", ""]
            out += [f"- {n} x {k}" for k, n in cp.most_common()]
        checks = Counter((r["records_path_same"], r.get("hbclock_eq_oracle"), r.get("tv"),
                          r.get("dump_policy"), json.dumps(r.get("chain"))) for r in ok)
        out += ["", "Checks (aggregates == records path, HbClock == oracle, tv_violation, "
                "dump hb_gate_policy, hb_chain):", ""]
        out += [f"- {n} x {k}" for k, n in checks.most_common()]
        out += ["", "Schedules (lock-word RMWs `b<block>:<pc>@<seq>[..<window end>)`, then the "
                "pair's read and write seqs):", ""]
        for k, n in Counter((r["node"], _sig(r)) for r in ok).most_common():
            out.append(f"- {k[0]}: {n} x `{k[1]}`")
        out.append("")
    Path(f"{a.root}/runs_summary.md").write_text("\n".join(out) + "\n")
    print("\n".join(out))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("record")
    g = r.add_mutually_exclusive_group(required=True)
    g.add_argument("--exe")
    g.add_argument("--src")
    r.add_argument("--label", required=True)
    r.add_argument("--store", required=True)
    r.add_argument("--mode", default="vector-clock", choices=("vector-clock", "scalar-clock"))
    r.add_argument("--policy", default="", choices=("", "recorded", "certain"))
    r.add_argument("--runs", type=int, default=1)
    r.add_argument("--timeout", type=int, default=300)
    an = sub.add_parser("analyze")
    an.add_argument("root")
    tb = sub.add_parser("tables")
    tb.add_argument("root")
    a = ap.parse_args()
    {"record": cmd_record, "analyze": cmd_analyze, "tables": cmd_tables}[a.cmd](a)


if __name__ == "__main__":
    main()
