#!/usr/bin/env bash
# done/total per stage for the follow-up sweep (sanitizer family, keep re-collect,
# diagnose, iGUARD build+run, spack, purge). Job ids come from setup/.job_* files.
cd /home/fzheng4/AccelProf/eval/baselines/setup || exit 1
st(){ s=$(squeue -j "$1" -h -o "%t" 2>/dev/null|sort|uniq -c|awk '{printf "%s%s ",$2,$1}'); [ -n "$s" ]&&echo "$s"||sacct -j "$1" -n -o State 2>/dev/null|head -1|tr -d ' '; }
ad(){ sacct -j "$1" -n -o JobID,State 2>/dev/null|grep -E "^${1}_[0-9]+ "|grep -cE "COMPLETED|FAILED|TIMEOUT|CANCELLED"; }
rows(){ cat /home/fzheng4/AccelProf/eval/results/baselines-$1-shard*.csv 2>/dev/null | grep -vc "^id,"; }
J_SAN=$(cat .job_sanitizer 2>/dev/null); J_KEEP=$(cat .job_keep 2>/dev/null); J_DIAG=$(cat .job_diag 2>/dev/null)
J_IG=$(cat .job_iguard 2>/dev/null); J_IGR=$(cat .job_iguard_run 2>/dev/null); J_SP=$(cat .job_spack 2>/dev/null)
PURGED=$(grep -l PURGE-DONE build_logs/purge-*.log 2>/dev/null | wc -l); PURGET=$(ls build_logs/purge-*.log 2>/dev/null | wc -l)
printf "PROGRESS %s | sanitizer(%s): %s/32 shards, %s/2544 runs [%s] | keep(%s): %s/32 [%s] | diag(%s): %s/23 [%s] | iguard-build(%s): %s %s | iguard-run(%s): %s/32 [%s] | spack(%s): %s | purge: %s/%s nodes\n" \
 "$(date +%H:%M)" "$J_SAN" "$(ad $J_SAN)" "$(rows sanitizer)" "$(st $J_SAN)" \
 "$J_KEEP" "$(ad $J_KEEP)" "$(st $J_KEEP)" "$J_DIAG" "$(ad $J_DIAG)" "$(st $J_DIAG)" \
 "$J_IG" "$(st $J_IG)" "$(grep -oE 'OK ->.*|BLOCKED.*' iguard.status 2>/dev/null | head -1 | cut -c1-60)" \
 "${J_IGR:-none}" "$( [ -n "$J_IGR" ] && ad $J_IGR || echo 0)" "$( [ -n "$J_IGR" ] && st $J_IGR)" \
 "$J_SP" "$(st $J_SP) $(grep -oE 'OK: [a-z-]+|FAIL: spack install [a-z-]+' spack.status 2>/dev/null | tr '\n' ' ')" "$PURGED" "$PURGET"
# cuVein re-run chain (run_rerun.sh): main 32 shards + P9 10 shards -> mid -> keep/diag -> final2
J_RR=$(cat .job_rerun 2>/dev/null); J_R9=$(cat .job_rerun_p9 2>/dev/null); J_RM=$(cat .job_rerun_mid 2>/dev/null); J_F2=$(cat .job_final2 2>/dev/null)
if [ -n "$J_RR" ]; then
  RROWS=$(cat /home/fzheng4/AccelProf/eval/results/baselines-cuvein-shard[0-9]*_32.csv 2>/dev/null | grep -vc "^id,")
  printf "RERUN %s | main(%s): %s/32 shards, %s/%s rows [%s] | p9(%s): %s/10 [%s] | mid(%s): %s | keep(%s): %s/32 [%s] | diag(%s): %s/%s [%s] | final2(%s): %s\n" \
   "$(date +%H:%M)" "$J_RR" "$(ad $J_RR)" "$RROWS" "$(( (754-10)*2*3 ))" "$(st $J_RR)" \
   "$J_R9" "$(ad $J_R9)" "$(st $J_R9)" "$J_RM" "$(st $J_RM)" \
   "${J_KEEP:-none}" "$( [ -n "$J_KEEP" ] && ad $J_KEEP || echo 0)" "$( [ -n "$J_KEEP" ] && st $J_KEEP)" \
   "${J_DIAG:-none}" "$( [ -n "$J_DIAG" ] && ad $J_DIAG || echo 0)" "$(grep -c . residual_ids.txt 2>/dev/null || echo ?)" "$( [ -n "$J_DIAG" ] && st $J_DIAG)" \
   "${J_F2:-none}" "$( [ -n "$J_F2" ] && st $J_F2)"
fi
# consolidated Indigo-original suite (run_indigo_full.sh): 4130 rows per tool
if [ -e .job_pi_build ]; then
  R=/home/fzheng4/AccelProf/eval/results
  n(){ cat $R/$1 2>/dev/null | cut -d, -f1 | grep "^PI-" | sort -u | wc -l; }
  T1=$(sqlite3 tools/HiRace/results/hirace_correctness_results.sqlite3 "select count(distinct code) from hirace" 2>/dev/null || echo "?")
  printf "INDIGO-FULL %s | build: %s | cuVein: %s/32 shards, %s/4130 ids [%s] | sanitizer: %s/32, %s/4130 [%s] | iGUARD: %s/32, %s/4130 [%s] | HiRace: %s/16, %s/4130 [%s] | SuperCollider: %s/4, %s/99 [%s] | final2: %s | make table1: %s/590 codes [%s %s]\n" \
   "$(date +%H:%M)" "$(st $(cat .job_pi_build))" \
   "$(ad $(cat .job_pi_cuvein))" "$(n 'baselines-cuvein-shardpi*_32.csv')" "$(st $(cat .job_pi_cuvein))" \
   "$(ad $(cat .job_pi_san))" "$(n 'baselines-sanitizer-shardpi*_32.csv')" "$(st $(cat .job_pi_san))" \
   "$(ad $(cat .job_pi_iguard))" "$(n 'baselines-iguard-shardpi*_32.csv')" "$(st $(cat .job_pi_iguard))" \
   "$(ad $(cat .job_pi_hirace))" "$(n 'baselines-hirace-shardpi*_16.csv')" "$(st $(cat .job_pi_hirace))" \
   "$(ad $(cat .job_pi_sc))" "$(n 'baselines-supercollider-shardpi*_4.csv')" "$(st $(cat .job_pi_sc))" \
   "$(st $(cat .job_pi_final))" "$T1" "$(st $(cat .job_pi_t1))" "$(st $(cat .job_pi_t1b))"
fi
