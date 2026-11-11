#!/bin/bash
# green set of CLAUDE.md A4 (the ScoR artifacts rm is skipped: ScoR is outside the sparse set) + test_r1_distance
cd /home/fzheng4/wt-m2
export PATH=/home/fzheng4/wt-m2/bin:$PATH
PY=/home/fzheng4/AccelProf/.env/bin/python
git rev-parse --short HEAD
$PY -m pytest python/test_sync_dominance.py python/test_barrier_soundness.py python/test_coherent_ldst.py python/test_atomic_memory_model.py python/test_barrier_exit.py python/test_hb_substitutions.py python/test_cp_async.py python/test_co_chain.py python/test_co_rules.py -q -rs 2>&1 | tail -40
echo ==== test_no_dump
$PY -m pytest python/test_no_dump.py -q -rs 2>&1 | tail -15
echo ==== test_r1_distance
$PY -m pytest python/test_r1_distance.py -q -rs 2>&1 | tail -15
