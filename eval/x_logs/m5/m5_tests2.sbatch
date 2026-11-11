#!/bin/bash
#SBATCH -p normal
#SBATCH -N 1
#SBATCH -t 01:00:00
#SBATCH -J m5-tests2
#SBATCH -o /home/fzheng4/wt-m5/eval/x_logs/m5/tests2-%j.log
# M5: per-file counts of the closure tests, CUVEIN_CHAIN_ATOMIC_HOP=1 and 0 (the test_co_chain autouse fixture pins the variable to 0 for the
# C6/C6b count tests; the M5 tests pass chain_atomic_hop explicitly), plus the base revision's test_co_chain.py (git show 4cb6547e) for comparison.
W=/home/fzheng4/wt-m5; PY=/home/fzheng4/AccelProf/.env/bin/python
cd $W
for v in $(env | grep -o '^\(CUVEIN\|YOSEMITE\)_[A-Z0-9_]*'); do unset $v; done
export ACCEL_PROF_HOME=$W CUVEIN_HOME=$W
echo "host=$(hostname) rev=$(git rev-parse --short=12 HEAD) $(date -Is)"
git show 4cb6547e:python/test_co_chain.py > python/test_co_chain_base4cb.py
for sw in 1 0; do
  for f in test_co_chain test_co_chain_base4cb test_co_rules test_verdict_parallel test_collector_only test_cp_async; do
    echo "== CUVEIN_CHAIN_ATOMIC_HOP=$sw $f: $(CUVEIN_CHAIN_ATOMIC_HOP=$sw $PY -m pytest python/$f.py -q -p no:cacheprovider -W ignore 2>&1 | tail -1)"
  done
done
rm -f python/test_co_chain_base4cb.py
echo end
