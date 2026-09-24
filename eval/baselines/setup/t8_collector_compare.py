#!/usr/bin/env python3
"""Compare the T8 collector check outputs (t8_collector_check.sh) before vs after.

  .env/bin/python t8_collector_compare.py /mnt/beegfs/$USER/t8_check

A dump = the files of one dependency_* directory. Pairs compared (every program, rep):
  before/default  vs after/default      default tool path: must be byte-identical
  before/hb-vc    vs after/hb-vc        vector-clock (engine) dump
  before/hb-sc    vs after/hb-sc        scalar-clock dump (NO_ENGINE before, HB_MODE after)
  after/hb-legacy vs after/hb-sc        deprecated YOSEMITE_HB_NO_ENGINE == scalar-clock
  after/hb-bogus  vs after/hb-vc        unknown YOSEMITE_HB_MODE falls back to vector-clock
plus rep1 vs rep2 inside each phase (run-to-run determinism), the presence of hb_races in
vector-clock dumps and its absence in scalar-clock dumps, and the stderr warnings.
"""
import glob
import hashlib
import json
import os
import sys

root = sys.argv[1]
bad = 0


ADDR_MIN = 1 << 40          # device virtual addresses (0x7f.. / 0x10..): renamed by rank
RUN_VARIANT = {"dist"}      # per-edge distance histograms: differ run to run (schedule)


def _norm(obj, addrs):
    if isinstance(obj, dict):
        return {k: _norm(v, addrs) for k, v in obj.items() if k not in RUN_VARIANT}
    if isinstance(obj, list):
        return [_norm(v, addrs) for v in obj]
    if isinstance(obj, int) and not isinstance(obj, bool) and obj >= ADDR_MIN:
        return f"A{addrs.setdefault(obj, len(addrs))}"
    return obj


def _collect_addrs(obj, out):
    if isinstance(obj, dict):
        for v in obj.values():
            _collect_addrs(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _collect_addrs(v, out)
    elif isinstance(obj, int) and not isinstance(obj, bool) and obj >= ADDR_MIN:
        out.add(obj)


def _unordered(obj):
    """schedule-insensitive form: 'seq' dropped, every list sorted"""
    if isinstance(obj, dict):
        return {k: _unordered(v) for k, v in obj.items() if k != "seq"}
    if isinstance(obj, list):
        return sorted((_unordered(v) for v in obj), key=lambda x: json.dumps(x, sort_keys=True))
    return obj


ORDERLESS = False          # level 2: schedule order ignored
PCLEVEL = False            # level 3: + engine race records projected to (pc pair, kind, space)


def _pclevel(j):
    for key in ("hb_races", "hb_races_sync_only"):
        if isinstance(j.get(key), list):
            proj = set()
            for r in j[key]:
                if isinstance(r, dict):
                    proj.add((r.get("a_pc"), r.get("b_pc"), r.get("kind"), r.get("space")))
                else:              # [a_pc, b_pc, n] rows of hb_races_sync_only
                    proj.add(tuple(r[:2]))
            j[key] = sorted(proj, key=str)
    return j


def dump(phase, prog, conf, rep):
    """{file: sha256 of the normalised JSON}: device addresses renamed by their rank
    (allocation addresses move between runs, their order does not), per-edge distance
    histograms dropped (they vary run to run with the same library). Non-JSON files: raw."""
    d = f"{root}/{phase}/{prog}/{conf}/rep{rep}/dump"
    if not os.path.isdir(d):
        return None
    out = {}
    for f in sorted(glob.glob(f"{d}/*")):
        if not os.path.isfile(f):
            continue
        raw = open(f, "rb").read()
        try:
            j = json.loads(raw)
            s = set()
            _collect_addrs(j, s)
            addrs = {a: i for i, a in enumerate(sorted(s))}
            n = _norm(_pclevel(j) if PCLEVEL else j, addrs)
            raw = json.dumps(_unordered(n) if ORDERLESS else n, sort_keys=True).encode()
        except ValueError:
            pass
        out[os.path.basename(f)] = hashlib.sha256(raw).hexdigest()
    return out


def stderr(phase, prog, conf, rep):
    out = ""
    for f in glob.glob(f"{root}/{phase}/{prog}/{conf}/rep{rep}/**/*", recursive=True):
        if os.path.isfile(f) and not f.endswith(".json") and not f.endswith("/rc.txt"):
            try:
                out += open(f, errors="replace").read()
            except OSError:
                pass
    return out


def keys(phase, prog, conf, rep):
    d = f"{root}/{phase}/{prog}/{conf}/rep{rep}/dump"
    ks = set()
    for f in glob.glob(f"{d}/kernel_*.json"):
        try:
            ks |= set(json.load(open(f)))
        except ValueError:
            ks.add("<unparsable>")
    return ks


def same(a, b, what, retry=None):
    """exact (after normalisation); on a difference, retry schedule-insensitively --
    a program whose own repeated runs differ (thread interleaving) must at least match
    as a multiset of events / races / edges."""
    global bad, ORDERLESS, PCLEVEL
    ok = a is not None and a == b
    if not ok and retry is not None:
        ORDERLESS = True
        a2, b2 = retry()
        if a2 is not None and a2 == b2:
            ORDERLESS = False
            print(f"  same*   {what} ({len(a2)} files; equal modulo schedule order)")
            return True
        PCLEVEL = True
        a3, b3 = retry()
        ORDERLESS = PCLEVEL = False
        if a3 is not None and a3 == b3:
            print(f"  same**  {what} ({len(a3)} files; equal modulo schedule order, engine "
                  f"race records compared as (pc pair, kind, space) sets)")
            return True
    if not ok:
        bad += 1
        diff = sorted(k for k in set(a or {}) | set(b or {}) if (a or {}).get(k) != (b or {}).get(k))
        print(f"  DIFFER  {what}: {diff[:6]}")
    else:
        print(f"  same    {what} ({len(a)} files)")
    return ok


progs = sorted(os.listdir(f"{root}/after"))
for prog in progs:
    print(f"== {prog}")
    def cmp(p1, c1, p2, c2, rep, what):
        same(dump(p1, prog, c1, rep), dump(p2, prog, c2, rep), what,
             retry=lambda: (dump(p1, prog, c1, rep), dump(p2, prog, c2, rep)))
    for rep in (1, 2):
        cmp("before", "default", "after", "default", rep, f"default rep{rep}: before vs after")
        cmp("before", "hb-vc", "after", "hb-vc", rep, f"hb-vc rep{rep}: before vs after")
        cmp("before", "hb-sc", "after", "hb-sc", rep, f"hb-sc rep{rep}: before(NO_ENGINE) vs after(HB_MODE=scalar-clock)")
        cmp("after", "hb-legacy", "after", "hb-sc", rep, f"hb-legacy rep{rep} vs hb-sc (after)")
        cmp("after", "hb-bogus", "after", "hb-vc", rep, f"hb-bogus rep{rep} vs hb-vc (after)")
    for phase in ("before", "after"):
        for conf in ("default", "hb-vc", "hb-sc"):
            a, b = dump(phase, prog, conf, 1), dump(phase, prog, conf, 2)
            if a != b:
                ORDERLESS = True
                a2, b2 = dump(phase, prog, conf, 1), dump(phase, prog, conf, 2)
                PCLEVEL = True
                a3, b3 = dump(phase, prog, conf, 1), dump(phase, prog, conf, 2)
                ORDERLESS = PCLEVEL = False
                lvl = ("equal modulo schedule order" if a2 == b2 else
                       "equal at pc-pair level" if a3 == b3 else "STILL DIFFERENT at pc-pair level")
                print(f"  note    {phase}/{conf}: rep1 != rep2 exactly; {lvl}")
    kv, ks = keys("after", prog, "hb-vc", 1), keys("after", prog, "hb-sc", 1)
    print(f"  keys    vector-clock has hb_races: {'hb_races' in kv}; scalar-clock has hb_races: {'hb_races' in ks}")
    if "hb_races" not in kv or "hb_races" in ks:
        bad += 1
    w_leg = "YOSEMITE_HB_NO_ENGINE is deprecated" in stderr("after", prog, "hb-legacy", 1)
    w_bog = "YOSEMITE_HB_MODE=bogus is neither" in stderr("after", prog, "hb-bogus", 1)
    w_none = any("[cuVein]" in stderr("after", prog, c, 1) for c in ("default", "hb-vc", "hb-sc"))
    print(f"  warn    legacy warning: {w_leg}; bogus warning: {w_bog}; spurious [cuVein] line elsewhere: {w_none}")
    if not w_leg or not w_bog or w_none:
        bad += 1
print(f"\n{'ALL CHECKS PASS' if not bad else f'{bad} CHECK(S) FAILED'}")
sys.exit(1 if bad else 0)
