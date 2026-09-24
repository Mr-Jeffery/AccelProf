#!/usr/bin/env bash
# Consolidated Indigo-original suite PI (all 590 IndigoSuite codes x 7 inputs) for every
# detector, replacing the partial sets P2/P8, plus the HiRace artifact's own `make table1`.
#   p_pi_build (CPU: 590 plain + 590 HiRace twins, manifest)
#   -> [cuVein ‖ compute-sanitizer ‖ iGUARD ‖ HiRace ‖ SuperCollider(99-subset rows)]  (GPU arrays)
#   -> p_final2 (merge incl. hirace, classify, tables)
#   ‖ p_hirace_table1 x2 (verbatim artifact run; second job resumes if the first hit its limit)
cd "$(dirname "$(readlink -f "$0")")" || exit 1
X="-x c54"
# the 21-pattern HiRace rows came from a glob bug (only *_hirace.cu): superseded, kept
S=/home/fzheng4/AccelProf/eval/results/superseded_hirace_21; mkdir -p $S
for f in /home/fzheng4/AccelProf/eval/results/baselines-hirace.csv; do [ -e "$f" ] && mv -n "$f" $S/; done
jb=$(sbatch --parsable p_pi_build.sh)
jc=$(sbatch --parsable --dependency=afterok:$jb $X p_pi_cuvein.sh)
js=$(sbatch --parsable --dependency=afterok:$jb $X p_pi_sanitizer.sh)
ji=$(sbatch --parsable --dependency=afterok:$jb $X p_pi_iguard.sh)
jh=$(sbatch --parsable --dependency=afterok:$jb $X p_pi_hirace.sh)
jx=$(sbatch --parsable --dependency=afterok:$jb $X p_pi_sc.sh)
jf=$(sbatch --parsable --dependency=afterany:$jc:$js:$ji:$jh:$jx p_final2.sh)
jt=$(sbatch --parsable $X p_hirace_table1.sh)
jt2=$(sbatch --parsable --dependency=afterany:$jt $X p_hirace_table1.sh)
for kv in build:$jb cuvein:$jc san:$js iguard:$ji hirace:$jh sc:$jx final:$jf t1:$jt t1b:$jt2; do echo "${kv#*:}" > .job_pi_${kv%%:*}; done
echo "build=$jb cuvein=$jc sanitizer=$js iguard=$ji hirace=$jh sc=$jx final2=$jf table1=$jt,$jt2"
