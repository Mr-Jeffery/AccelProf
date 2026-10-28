# cuml-tsne-new-1: ML::TSNE::BH::RepulsionKernel dq / pos / node shared-memory races (barnes_hut_kernels.cuh L596, L625-632, L647) (T21c candidate).
# Pinned (buggy) c7e7738bb6386186bc031d821e71ce1c1abfe3c8 (rapidsai/cuml, 2026-10-13); no fix commit, only the buggy variant is built.
# ROUTE R2, not R1.  R1 would be libcuml built by cpp/CMakeLists.txt at the pinned commit, which fetches (rapids-cmake CPM) CCCL, RMM, RAFT, cuVS (and its FAISS/HNSW
# dependencies), Treelite, nvForest, GPUTreeSHAP, rapids-logger, GTest/GBench and the rapids-cmake version pins themselves from GitHub at configure time; the compute nodes have no
# internet, the partial clone of cuml is tree:0, and only rapids-cmake, rapids-logger, rmm, fmt and spdlog bare clones exist under ~/incoming/realworld/deps (cuVS, RAFT at
# cuml's pin, Treelite, nvForest, FAISS are absent).  Fetching ~10 repositories at the exact pins and building libcuml++ (CUDA 13.4, sm_89) is a multi-hour build with an
# open-ended chance of CCCL 3 / CUDA 13 incompatibilities in RAFT and cuVS; declared infeasible per the 2-3 hour budget.
# R2: five files copied byte-for-byte from the pinned commit with `git cat-file blob` (r2_extract.sh; r2/verbatim.check shows blob sha1 == hash-object):
#   cpp/src/tsne/barnes_hut_kernels.cuh   (the kernels, incl. RepulsionKernel)
#   cpp/src/tsne/utils.cuh                (included by the kernels)
#   cpp/src/tsne/barnes_hut_tsne.cuh      (the host orchestration ML::TSNE::Barnes_Hut: launches all BH kernels in the order the library does)
#   cpp/include/cuml/common/checked_arithmetic.hpp, cpp/include/cuml/manifold/tsne.h  (TSNEParams)
# r2/common/stubs/ holds minimal stand-ins for what those files include from RAFT / RMM / cuML (rapids_logger level_enum + disabled logger, CUML_KERNEL = "__global__ static"
# as in the pinned cuml/common/utils.hpp, raft::{WarpSize, ceildiv, copy, getMultiProcessorCount, handle_t, linalg::scalarMultiply, random::Rng}, rmm::{device_uvector,
# device_scalar, exec_policy}, RAFT_FAIL/RAFT_CUDA_TRY); r2/common/main.cu is the host driver.  No kernel file is modified.
# Flags follow cpp/cmake/modules/ConfigureCUDA.cmake and CMakeLists.txt at the pinned commit: C++20, --expt-extended-lambda --expt-relaxed-constexpr, Release (-O3 -DNDEBUG),
# CUDA_ENABLE_LINE_INFO -> -lineinfo, no -G; -Werror=all-warnings and fatbin compression are not used.
# Driver: 1,000 2-D points in four clusters, 8-NN symmetrised COO P (all equal values, sum 1, ~12,000 entries), TSNE_INIT::PCA (Y supplied), 1 iteration (max_iter=1: one launch of every BH kernel).
T_ROUTE=R2; T_KERNEL=RepulsionKernel; T_SPACE=shared; T_EXE=driver; T_ARTIFACTS="driver"
t_export() { echo "R2: files live in $TDIR/r2"; }
t_build() {    # cwd = $OUT (node-local); sources unpacked: $SRC/cpp/... (verbatim) and $SRC/common/ (stubs + main)
  nvcc -std=c++20 -O3 -DNDEBUG $RW_NVCC_FLAGS $RW_LINEINFO --expt-extended-lambda --expt-relaxed-constexpr \
       -I"$SRC/common/stubs" -I"$SRC/cpp/include" -I"$SRC/cpp/src/tsne" -o driver "$SRC/common/main.cu" > build.log 2>&1 || { tail -60 build.log; return 1; }
  grep -c "warning" build.log | sed 's/^/nvcc warnings: /'
  cp build.log build-warnings.txt
}
t_cmd() { echo "$ART/driver 1000 1"; }
