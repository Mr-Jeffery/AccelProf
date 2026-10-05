#!/usr/bin/env bash
# cuVein-only re-run after a detector revision (other tools' rows are kept).
#   cuvein_rev.sh (pin revision, CPU)  -> supersede_prefix.sh (move pre-fix rows aside)
#   -> [p_rerun.sh 32 shards ‖ p_rerun_p9.sh 10 shards]  (GPU)
#   -> p_rerun_mid.sh (merge, follow-up id lists; submits p_keep ‖ p_diagnose -> p_final2)
# The smoke gate (fpfix_smoke_ids.txt, both modes, srun) is run by hand before this;
# see setup/smoke_rev/. Prints the job ids; progress via setup/progress.sh.
cd "$(dirname "$(readlink -f "$0")")" || exit 1
bash cuvein_rev.sh || { echo "revision check BLOCKED (see cuvein_rev.status)"; exit 3; }
bash supersede_prefix.sh
X="-x c54"   # c54: dead NVIDIA driver
jr=$(sbatch --parsable $X p_rerun.sh)
j9=$(sbatch --parsable $X p_rerun_p9.sh)
jm=$(sbatch --parsable --dependency=afterany:$jr:$j9 p_rerun_mid.sh)
echo "$jr" > .job_rerun; echo "$j9" > .job_rerun_p9; echo "$jm" > .job_rerun_mid
rm -f .job_keep .job_diag .job_final2
echo "rerun=$jr p9=$j9 mid=$jm"
