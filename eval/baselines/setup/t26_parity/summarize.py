#!/usr/bin/env python3
"""T26 parity: tally the co_json_diff.py lines of fixtures.sh / t20.sh / synth.sh logs by check.

    summarize.py LOG...

A check is the text between the program name and EQUAL/DIFFER/NO-KERNELS ("fidelity: ...",
"same-stream: ...", "live: ..."). Per log and check: programs EQUAL, DIFFER, NO-KERNELS, and the summed
kernels / byte-identical kernels / differing kernels; then the programs behind every non-EQUAL line.
"""
import collections
import re
import sys

LINE = re.compile(r"^(?P<prog>\S+) (?P<check>.+?) (?P<res>EQUAL|DIFFER|NO-KERNELS)(?P<rest>.*)$")


def main():
    for log in sys.argv[1:]:
        tally = collections.OrderedDict()
        bad = collections.defaultdict(list)
        for ln in open(log, errors="replace"):
            m = LINE.match(ln.rstrip("\n"))
            if not m:
                continue
            ck = m["check"]
            t = tally.setdefault(ck, collections.Counter())
            t[m["res"]] += 1
            kv = dict(re.findall(r"(\w+)=(\d+)", m["rest"]))
            for k in ("kernels", "bytes_equal", "differ"):
                t[k] += int(kv.get(k, 0))
            if m["res"] != "EQUAL":
                bad[ck].append(f"{m['prog']} {m['res']}{m['rest'][:160]}")
        print(f"### {log}")
        for ck, t in tally.items():
            print(f"  {ck}: programs EQUAL {t['EQUAL']}, DIFFER {t['DIFFER']}, NO-KERNELS {t['NO-KERNELS']}; "
                  f"kernels {t['kernels']}, byte-identical {t['bytes_equal']}, differing {t['differ']}")
        for ck, rows in bad.items():
            print(f"  -- not EQUAL, {ck}:")
            for r in rows:
                print(f"     {r}")


if __name__ == "__main__":
    main()
