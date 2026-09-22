#!/usr/bin/env bash
# Orchestrate the full parallel run: build(CPU) -> {collect(GPU array), racecheck
# (GPU)} -> analyze(CPU array) -> finalize(CPU). Prints the job chain.
cd "$(dirname "$0")" || exit 1
jb=$(sbatch --parsable p_build.sh)
jc=$(sbatch --parsable --dependency=afterok:$jb p_collect.sh)
jr=$(sbatch --parsable --dependency=afterok:$jb p_racecheck.sh)
ja=$(sbatch --parsable --dependency=afterok:$jc p_analyze.sh)
jf=$(sbatch --parsable --dependency=afterok:$ja:$jr p_finalize.sh)
echo "build=$jb collect(array)=$jc racecheck=$jr analyze(array)=$ja finalize=$jf"
