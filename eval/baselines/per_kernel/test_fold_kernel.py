import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import kfold as kf


def run(v, launched, reporting=()):
    return dict(verdict=v, launched=set(launched), reporting=set(reporting))


def test_several_launches_one_reporting():
    # launches fold into the kernel: one reporting launch makes the kernel RACE; the other kernel stays CLEAN
    runs = [run("RACE", {"init", "main"}, {"main"})]
    assert kf.fold_kernels(runs, {"init", "main"}) == {"init": "CLEAN", "main": "RACE"}


def test_kernel_with_no_finished_launch_is_timeout():
    runs = [run("CLEAN", {"a", "b"}), run("TIMEOUT", {"a"})]
    assert kf.fold_kernels(runs, {"a", "b"}) == {"a": "CLEAN", "b": "TIMEOUT"}
    # an errored run without a launch is ERROR, not TIMEOUT
    runs = [run("CLEAN", {"a", "b"}), run("ERROR", {"a"})]
    assert kf.fold_kernels(runs, {"a", "b"})["b"] == "ERROR"


def test_never_launched_kernel_is_not_counted():
    runs = [run("CLEAN", {"a"}), run("CLEAN", {"a"})]
    u = kf.universe_of(runs)
    assert u == {"a"} and "never" not in kf.fold_kernels(runs, u)


def test_report_in_race_free_kernel_of_racy_binary():
    runs = [run("RACE", {"distance", "reduce"}, {"distance", "reduce"})]
    kv = kf.fold_kernels(runs, {"distance", "reduce"})
    labels = {("b", "distance"): "RACE", ("b", "reduce"): "CLEAN"}
    c = kf.confusion_k([("b", k) for k in kv], labels, {("b", k): v for k, v in kv.items()})
    assert (c["tp"], c["fp"], c["fn"], c["tn"]) == (1, 1, 0, 0)


def test_race_wins_over_missing_launch():
    runs = [run("TIMEOUT", {"a"}, {"a"}), run("TIMEOUT", set())]
    assert kf.fold_kernel("a", runs) == "RACE"


def test_fold_back_equals_per_binary_fold():
    # the per-binary rule of make_tables.fold_verdict applied to the runs equals fold_back over the kernels,
    # whenever every kernel is launched by every run or the binary has a RACE
    import itertools
    mt_fold = lambda vs: ("RACE" if "RACE" in vs else "CLEAN" if all(v == "CLEAN" for v in vs)
                          else "TIMEOUT" if "TIMEOUT" in vs else "ERROR")
    ks = {"a", "b"}
    for vs in itertools.product(["RACE", "CLEAN", "TIMEOUT"], repeat=2):
        runs = []
        for v in vs:
            if v == "RACE":
                runs.append(run(v, ks, {"a"}))
            elif v == "CLEAN":
                runs.append(run(v, ks))
            else:
                runs.append(run(v, set()))      # the cap struck before any kernel finished
        assert kf.fold_back(kf.fold_kernels(runs, ks)) == mt_fold(list(vs)), vs
