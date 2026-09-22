#!/usr/bin/env bash
#SBATCH --job-name=cv-rerun-mid
#SBATCH --partition=normal
#SBATCH --nodes=1 --ntasks=1
#SBATCH --time=00:20:00
#SBATCH --output=/home/fzheng4/AccelProf/eval/baselines/setup/build_logs/rerun-mid-%j.log
# After the re-run arrays: merge the new cuVein shards and derive the follow-up id
# lists (keep / residual) from them, then submit the keep + diagnose arrays and the
# final merge/classify/tables job (submitted here because the diagnose array size
# depends on the residual count). CPU only.
cd /home/fzheng4/AccelProf || exit 1
source eval/baselines/gpu_env.sh
S=eval/baselines/setup
$PY eval/baselines/parallel.py merge --tool cuvein
$PY $S/mk_followup_ids.py | tee $S/build_logs/rerun-mid-ids.txt
NK=$(grep -c . $S/keep_all_ids.txt); NR=$(grep -c . $S/residual_ids.txt)
X="-x c54"
if [ "$NK" -gt 0 ]; then
  jk=$(sbatch --parsable $X $S/p_keep.sh); echo "$jk" > $S/.job_keep   # p_keep shards /32 (fixed)
fi
if [ "$NR" -gt 0 ]; then
  jd=$(sbatch --parsable $X --array=0-$((NR-1)) $S/p_diagnose.sh); echo "$jd" > $S/.job_diag
fi
dep=$(printf "%s:%s" "${jk:-}" "${jd:-}" | sed 's/^://; s/:$//')
jf=$(sbatch --parsable ${dep:+--dependency=afterany:$dep} $S/p_final2.sh); echo "$jf" > $S/.job_final2
echo "mid done: keep=$NK ids job=${jk:-none} diag=$NR ids job=${jd:-none} final2=$jf"
