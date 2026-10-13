#!/usr/bin/env bash
# Full sweep orchestrator (SLURM). Prints the job chain.
#   build(CPU) -> cuVein run(GPU array) -> final(CPU)
#   + compute-sanitizer family (GPU array)            [independent]
#   + HiRace box (GPU)                                [independent]
#   + spack deps (CPU) + iGUARD build box (GPU) -> iGUARD run (GPU array)
#   + purge scratch -> keep re-collect (FP/FN traces) + diagnose residuals
#   final2(CPU): merge all families -> classify_residuals -> classify_endpoints -> make_tables
cd "$(dirname "$(readlink -f "$0")")" || exit 1
X="-x c54"   # c54: dead NVIDIA driver (no CUDA-capable device) at the time of writing
jb=$(sbatch --parsable p_full_build.sh)
jr=$(sbatch --parsable --dependency=afterok:$jb $X p_full_run.sh)
jf=$(sbatch --parsable --dependency=afterany:$jr p_full_final.sh)
jh=$(sbatch --parsable -p rtx4060ti16g $X -N1 -n1 -t 03:00:00 -o build_logs/hirace_setup-%j.log hirace_setup.sh)
js=$(sbatch --parsable -p normal -N1 -n1 -c 8 -t 03:00:00 -o build_logs/spack_setup-%j.log spack_setup.sh)
ji=$(sbatch --parsable -p rtx4060ti16g $X -N1 -n1 -t 03:00:00 -o build_logs/iguard_setup-%j.log iguard_setup.sh)
jig=$(sbatch --parsable --dependency=afterany:$ji:$jf $X p_iguard.sh)
jsan=$(sbatch --parsable --dependency=afterany:$jf $X p_sanitizer.sh)
bash purge_scratch.sh >/dev/null
jk=$(sbatch --parsable --dependency=afterany:$jf $X p_keep.sh)
jd=$(sbatch --parsable --dependency=afterany:$jf $X p_diagnose.sh)
jsb=$(sbatch --parsable --dependency=afterany:$jf p_sc_build.sh)   # P8/P9 = SuperCollider-matched sets
jsc=$(sbatch --parsable --dependency=afterok:$jsb p_supercollider.sh)
jso=$(sbatch --parsable --dependency=afterok:$jsb:$ji p_sc_others.sh)
jf2=$(sbatch --parsable --dependency=afterany:$jig:$jsan:$jk:$jd:$jh:$jsc:$jso p_final2.sh)
echo "$js" > .job_spack; echo "$ji" > .job_iguard; echo "$jig" > .job_iguard_run
echo "$jsan" > .job_sanitizer; echo "$jk" > .job_keep; echo "$jd" > .job_diag
echo "build=$jb run=$jr final=$jf hirace=$jh spack=$js iguard_build=$ji iguard_run=$jig sanitizer=$jsan keep=$jk diag=$jd final2=$jf2"
