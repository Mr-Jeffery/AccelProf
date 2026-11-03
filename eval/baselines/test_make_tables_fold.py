"""X10: tests of the per-binary fold in make_tables.py (no GPU, no result CSVs needed)."""
import os
import sys

import pytest

sys.argv = [sys.argv[0]]          # make_tables reads its flags at import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_tables as mt  # noqa: E402

T = ("racecheck", "")


def _man(rows):
    return {i: dict(id=i, exe=exe, label=lab) for i, exe, lab in rows}


def _runs(vs):
    return {(i, T[0], T[1]): dict(verdict=v, notes="") for i, v in vs.items()}


def _fold(rows, vs):
    man = _man(rows)
    return mt.fold_binaries(_runs(vs), list(man), man, [T])


def test_race_on_one_input_reports_the_binary():
    f = _fold([("a1", "binA", "RACE"), ("a2", "binA", "RACE"), ("a3", "binA", "RACE")],
              {"a1": "CLEAN", "a2": "RACE", "a3": "CLEAN"})
    assert f["binA"]["v"][T] == "RACE"
    assert f["binA"]["rep"][T] == ["a2"]
    c, _ = mt.confusion_b(f, *T)
    assert (c["tp"], c["fn"], c["n"]) == (1, 0, 1)


def test_all_clean_is_clean():
    f = _fold([("a1", "binA", "CLEAN"), ("a2", "binA", "CLEAN")], {"a1": "CLEAN", "a2": "CLEAN"})
    assert f["binA"]["v"][T] == "CLEAN"
    assert mt.confusion_b(f, *T)[0]["tn"] == 1


def test_clean_plus_timeout_is_timeout():
    f = _fold([("a1", "binA", "RACE"), ("a2", "binA", "RACE")], {"a1": "CLEAN", "a2": "TIMEOUT"})
    assert f["binA"]["v"][T] == "TIMEOUT"
    c, ids = mt.confusion_b(f, *T)
    assert (c["to"], c["fn"], ids["to"]) == (1, 0, ["binA"])


def test_race_beats_timeout_and_error():
    assert mt.fold_verdict(["TIMEOUT", "RACE", "ERROR"]) == "RACE"


def test_error_only_is_error_and_clean_plus_error_is_error():
    assert mt.fold_verdict(["ERROR", "ERROR"]) == "ERROR"
    assert mt.fold_verdict(["CLEAN", "ERROR"]) == "ERROR"
    assert mt.fold_verdict([]) is None


def test_label_mismatch_raises():
    with pytest.raises(ValueError):
        _fold([("a1", "binA", "RACE"), ("a2", "binA", "CLEAN")], {"a1": "RACE", "a2": "CLEAN"})


def test_partial_race_row_counts():
    # a partial row keeps the harness verdict RACE; the fold must keep it
    f = _fold([("a1", "binA", "RACE"), ("a2", "binA", "RACE")], {"a1": "RACE", "a2": "TIMEOUT"})
    assert f["binA"]["v"][T] == "RACE"


def test_racy_and_fixed_builds_are_two_binaries():
    f = _fold([("p-racy-s", "bin_racy", "RACE"), ("p-racy-l", "bin_racy", "RACE"),
               ("p-fixed-s", "bin_fixed", "CLEAN"), ("p-fixed-l", "bin_fixed", "CLEAN")],
              {"p-racy-s": "RACE", "p-racy-l": "CLEAN", "p-fixed-s": "RACE", "p-fixed-l": "CLEAN"})
    c, ids = mt.confusion_b(f, *T)
    assert (c["tp"], c["fp"], c["n"]) == (1, 1, 2)
    assert ids["fp"] == ["bin_fixed"]


def test_tool_rows_on_our_ids_fold_to_our_binary():
    # HiRace / SuperCollider rows carry the manifest id of the program they stand for,
    # so their instrumented build folds into the same binary
    man = _man([("x1", "binX", "RACE"), ("x2", "binX", "RACE")])
    runs = {("x1", "hirace", ""): dict(verdict="CLEAN", notes=""),
            ("x2", "hirace", ""): dict(verdict="RACE", notes="")}
    f = mt.fold_binaries(runs, list(man), man, [("hirace", "")])
    assert list(f) == ["binX"] and f["binX"]["v"][("hirace", "")] == "RACE"


def test_coverage_records_missing_inputs():
    man = _man([("a1", "binA", "RACE"), ("a2", "binA", "RACE")])
    f = mt.fold_binaries(_runs({"a1": "CLEAN"}), list(man), man, [T])
    assert f["binA"]["cover"][T] == (1, 2)


def test_binary_key_falls_back_to_id():
    assert mt.binary_key("nope", {}) == "id:nope"
