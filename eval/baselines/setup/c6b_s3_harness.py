#!/usr/bin/env python3
"""C6b step 3 harness: run `parallel.py analyze` (collector-only mode, the unmodified verdict layer) on the hb-stripped store with
the kernel JSON loader of sync_dominance replaced by a guarded one (the only change, made in this process; python/ is untouched):
  * every kernel JSON is parsed with an object_hook that REFUSES a dict holding an hb_* key (HbGuardError) and returns a GuardDict;
  * GuardDict.__getitem__/get/__contains__/pop/setdefault: an access to an hb_* key that is PRESENT raises HbGuardError
    ("value read"); a probe of an hb_* key that is ABSENT is counted per call site (the unmodified verdict layer probes e.g.
    trace.get("hb_races") on every dump, collector-only included; the answer is the key-absent default) and, with S3_STRICT=1,
    raises as well;
  * sd.analyze is wrapped to append the probes of each call to $S3_PROBES/probes-<pid>.jsonl.
Usage: S3_PROBES=<dir> python c6b_s3_harness.py <parallel.py analyze args...>"""
import collections
import json
import os
import sys

W = os.environ["CUVEIN_HOME"]
sys.path.insert(0, f"{W}/eval/baselines")
sys.path.insert(0, f"{W}/python")
import parallel  # noqa: E402
import run_cuvein as rc  # noqa: E402

sd = rc.sd
PROBES = os.environ.get("S3_PROBES", "")
STRICT = os.environ.get("S3_STRICT") == "1"
_real_json = sd.json


class HbGuardError(RuntimeError):
    pass


_probe = collections.Counter()      # (site, key) -> n, this process, current analyze call
_reads = [0]


def _site():
    f = sys._getframe(3)
    return f"{os.path.basename(f.f_code.co_filename)}:{f.f_lineno}"


def _hb(k):
    return isinstance(k, str) and k.startswith("hb_")


class GuardDict(dict):
    def _chk(self, k):
        if _hb(k):
            if dict.__contains__(self, k):
                _reads[0] += 1
                raise HbGuardError(f"read of present hb key {k!r}")
            _probe[(_site(), k)] += 1
            if STRICT:
                raise HbGuardError(f"STRICT: probe of hb key {k!r} at {_site()}")

    def __getitem__(self, k):
        self._chk(k)
        return dict.__getitem__(self, k)

    def get(self, k, d=None):
        self._chk(k)
        return dict.get(self, k, d)

    def __contains__(self, k):
        self._chk(k)
        return dict.__contains__(self, k)

    def pop(self, k, *a):
        self._chk(k)
        return dict.pop(self, k, *a)

    def setdefault(self, k, d=None):
        self._chk(k)
        return dict.setdefault(self, k, d)


def _hook(d):
    for k in d:
        if _hb(k):
            _reads[0] += 1
            raise HbGuardError(f"hb key {k!r} present in a kernel JSON handed to the verdict layer")
    return GuardDict(d)


class _JsonShim:
    """sync_dominance's `json`: loads() guarded, everything else the real module."""
    def loads(self, s, **kw):
        return _real_json.loads(s, object_hook=_hook, **kw)

    def __getattr__(self, n):
        return getattr(_real_json, n)


sd.json = _JsonShim()
_orig_analyze = sd.analyze


def analyze(dot, kj, *a, **kw):
    _probe.clear()
    _reads[0] = 0
    try:
        return _orig_analyze(dot, kj, *a, **kw)
    finally:
        if PROBES:
            rec = {"kj": str(kj), "reads": _reads[0],
                   "probes": {f"{s}|{k}": n for (s, k), n in _probe.items()}}
            with open(f"{PROBES}/probes-{os.getpid()}.jsonl", "a") as f:
                f.write(json.dumps(rec) + "\n")


sd.analyze = analyze

if __name__ == "__main__":
    sys.argv = ["parallel.py"] + sys.argv[1:]
    parallel.main()
