# raft-1: raft::matrix::detail::select::radix::radix_kernel, __syncthreads missing between __threadfence() and thread 0's atomicInc
# (last-block-done pattern, global-memory histogram).  Fix e39ec7882e (2026-05-27), parent 32df870d05 (2026-05-22).  Route R1h.
#
# R1h for raft: our own driver (driver.cu) is compiled against the checkout's headers (raft cpp/include of the exact commit, placed
# FIRST on the include path).  raft's headers are NOT self-contained, so the tarball also carries the dependencies, pinned below and
# identical for both variants:  rmm (headers + compiled sources), rapids-logger (header + compiled source), spdlog (header + compiled
# sources).  CCCL, CUDA runtime, nvtx3 come from the toolkit (raft is not a CCCL target; its CMake would fetch CCCL 3.4.0 via CPM,
# the toolkit on the nodes, CUDA 13.4, ships its own CCCL).  The CMake-generated headers (logger_macros.hpp of raft and rmm)
# are produced in t_build by the same substitution CMake's configure_file does (see gen_headers below).
T_ROUTE=R1h; T_KERNEL=radix_kernel; T_SPACE=global; T_RACECHECK=na; T_EXE=driver
T_ARTIFACTS="driver h_proof.txt hdr.log.headers deps.txt"

# Pinned dependency revisions (NOT in the record; same for both variants).  Why:
#   rmm          5fd6cee381d9 (2026-05-22): dated like the buggy commit (raft 32df870d is 2026-05-22); pin chosen by the coordinator.
#   rapids-logger 4c72b598f99c (v0.2.3): the revision rapids-cmake@a773bfa (main on 2026-05-22 20:00 UTC) pins in
#                 rapids-cmake/cpm/versions.json for rapids_logger, i.e. what raft's and rmm's CMake would fetch.  (Newer
#                 rapids-logger main needs std::format = C++20 <format>, absent in the nodes' gcc 12.4; this pin does not.)
#   spdlog       v1.14.1 and fmt 11.0.2 are what rapids-logger 4c72b598 itself pins (CMakeLists.txt get_spdlog/get_fmt); with its
#                 default (BUILD_SHARED_LIBS=ON => RAPIDS_LOGGER_HIDE_ALL_SPDLOG_SYMBOLS=ON => FMT_OPTION BUNDLED) spdlog uses
#                 its BUNDLED fmt, so the external fmt 11.0.2 is not needed and not used.
RW_RMM_SHA=5fd6cee381d91155e10cd28063e7ab9b95c0a73c
RW_RLOG_SHA=4c72b598f99c8aa06af49468b3fc82f3931c6bf6
RW_SPDLOG_SHA=27cb4c76708608465c413f6d0e6b8d99a4d84302   # tag v1.14.1

rw_prefetch() {   # rw_prefetch <repo.git> <sha> <path>...   fetch the missing blobs in batches (partial clone), as export_rev.sh does
  local repo=$1 sha=$2; shift 2
  git -C "$repo" ls-tree -r "$sha" -- "$@" | awk '$2=="blob"{print $3}' | sort -u |
    xargs -r -n 400 git -C "$repo" -c fetch.negotiationAlgorithm=noop fetch --no-tags --no-write-fetch-head -q origin
}

t_export() {      # $1 variant, $2 raft sha, $3 out.tar.gz  (login node; one gzip of concatenated tar streams, unpacked by `tar -xizf`)
  local raft=$INCOMING/raft.git d=$INCOMING/deps
  local full; full=$(git -C "$raft" rev-parse --verify "$2^{commit}") || return 1
  rw_prefetch "$raft" "$full" cpp/include
  rw_prefetch "$d/rmm.git" $RW_RMM_SHA cpp/include cpp/src
  rw_prefetch "$d/rapids-logger.git" $RW_RLOG_SHA include src cmake VERSION
  rw_prefetch "$d/spdlog.git" $RW_SPDLOG_SHA include src
  { git -C "$raft" archive --format=tar --prefix=raft/ "$full" cpp/include
    git -C "$d/rmm.git" archive --format=tar --prefix=deps/rmm/ $RW_RMM_SHA cpp/include cpp/src
    git -C "$d/rapids-logger.git" archive --format=tar --prefix=deps/rapids-logger/ $RW_RLOG_SHA include src cmake VERSION
    git -C "$d/spdlog.git" archive --format=tar --prefix=deps/spdlog/ $RW_SPDLOG_SHA include src
  } | gzip -n > "$3" || return 1
  echo "t_export raft-1/$1: raft $full + rmm $RW_RMM_SHA + rapids-logger $RW_RLOG_SHA + spdlog $RW_SPDLOG_SHA -> $3 ($(du -sh "$3" | cut -f1), $(tar -xizOf "$3" 2>/dev/null | wc -c) bytes)"
}

# ---- build helpers ------------------------------------------------------------------------------------------------------
gen_headers() {   # the files CMake generates (cpp/CMakeLists.txt of raft, rmm; rapids-logger cmake/create_logger_macros.cmake)
  local g=$OUT/gen
  mkdir -p $g/raft/core $g/rmm
  # (include/{raft,rmm}/version_config.hpp, written by rapids_cmake_write_version_file, is included by no header of these trees: not generated)
  # create_logger_macros(<prefix> "<default logger>" <dir>): configure_file(cmake/logger_macros.hpp.in) = two @VAR@ substitutions
  local in=$SRC/deps/rapids-logger/cmake/logger_macros.hpp.in
  sed -e 's/@_RAPIDS_LOGGER_MACRO_PREFIX@/RAFT/g' -e 's/@_RAPIDS_LOGGER_DEFAULT_LOGGER@/raft::default_logger()/g' $in > $g/raft/core/logger_macros.hpp
  sed -e 's/@_RAPIDS_LOGGER_MACRO_PREFIX@/RMM/g'  -e 's/@_RAPIDS_LOGGER_DEFAULT_LOGGER@/rmm::default_logger()/g'  $in > $g/rmm/logger_macros.hpp
  grep -q '@_RAPIDS' $g/raft/core/logger_macros.hpp $g/rmm/logger_macros.hpp && { echo "gen_headers: unsubstituted @VAR@"; return 1; }
  return 0
}

build_deps() {    # libdeps.a = rmm (src/*.cpp, as listed in rmm/cpp/CMakeLists.txt) + rapids-logger (src/logger.cpp) + spdlog 1.14.1 (compiled lib)
  local sd=$SRC/deps
  local cuda_inc="-isystem ${CUDA_HOME:-/usr/local/cuda}/include/cccl -isystem ${CUDA_HOME:-/usr/local/cuda}/include"
  mkdir -p $OUT/o_deps
  # rmm: CXX_STANDARD 17, hidden visibility, PIC, Release (-O3 -DNDEBUG); -Wall/-Werror of the project are not reproduced
  local rmm_srcs; rmm_srcs=$(cd $sd/rmm/cpp && find src -name '*.cpp' | sort)
  local flags="-std=c++17 -O3 -DNDEBUG -fPIC -fvisibility=hidden"
  { for f in $rmm_srcs; do
      echo "g++ $flags -I$sd/rmm/cpp/include -I$OUT/gen -I$sd/rapids-logger/include $cuda_inc -c $sd/rmm/cpp/$f -o $OUT/o_deps/rmm_$(echo $f | tr / _).o"
    done
    echo "g++ $flags -I$sd/rapids-logger/include -I$sd/spdlog/include -DSPDLOG_COMPILED_LIB -c $sd/rapids-logger/src/logger.cpp -o $OUT/o_deps/rlogger.o"
    for f in spdlog cfg stdout_sinks color_sinks file_sinks async bundled_fmtlib_format; do
      echo "g++ $flags -I$sd/spdlog/include -DSPDLOG_COMPILED_LIB -c $sd/spdlog/src/$f.cpp -o $OUT/o_deps/spdlog_$f.o"
    done
  } > $OUT/deps_cmds.txt
  xargs -P ${NJOBS:-8} -I{} bash -c '{}' < $OUT/deps_cmds.txt || return 1
  rm -f libdeps.a; ar rcs libdeps.a $OUT/o_deps/*.o || return 1
  { echo "rmm $RW_RMM_SHA (cpp/src: $(echo "$rmm_srcs" | wc -l) files)"; echo "rapids-logger $RW_RLOG_SHA (src/logger.cpp)"; echo "spdlog $RW_SPDLOG_SHA v1.14.1 (compiled lib, bundled fmt)"
    echo "host g++: $(g++ --version | head -1); nvcc: $(nvcc --version | tail -2 | head -1)"; echo "objects: $(ls $OUT/o_deps | wc -l)"; } > deps.txt
}

# the include path of the driver: the checkout's raft headers first (R1h), then the generated headers, rmm, rapids-logger.
raft_incs() { echo "-I$SRC/raft/cpp/include -I$OUT/gen -I$SRC/deps/rmm/cpp/include -I$SRC/deps/rapids-logger/include"; }
# flags from raft's cpp/CMakeLists.txt + cmake/modules/ConfigureCUDA.cmake (Release, C++17):  --expt-extended-lambda --expt-relaxed-constexpr,
# RAFT_LOG_ACTIVE_LEVEL=RAPIDS_LOGGER_LOG_LEVEL_INFO, RAFT_SYSTEM_LITTLE_ENDIAN=1, CUDA_API_PER_THREAD_DEFAULT_STREAM, deprecation warnings off
# (DISABLE_DEPRECATION_WARNINGS=ON by default); no -Werror, no fatbin compression, no OpenMP (not needed for select_k).
raft_flags() { echo "-std=c++17 -O3 -DNDEBUG --expt-extended-lambda --expt-relaxed-constexpr -DRAFT_LOG_ACTIVE_LEVEL=RAPIDS_LOGGER_LOG_LEVEL_INFO -DRAFT_SYSTEM_LITTLE_ENDIAN=1 -DCUDA_API_PER_THREAD_DEFAULT_STREAM -DRAFT_HIDE_DEPRECATION_WARNINGS -Xcompiler=-Wno-deprecated-declarations"; }

t_build() {
  gen_headers || return 1
  build_deps || return 1
  local incs flags; incs=$(raft_incs); flags=$(raft_flags)
  # rmm/rapids-logger/spdlog are linked statically (libdeps.a), CUDA runtime statically (nvcc default).  gcc 12.4 on the nodes has no
  # libstdc++.a, so libstdc++ is dynamic; an rpath to the compiler's lib dir makes the binary independent of LD_LIBRARY_PATH.
  local gccdir; gccdir=$(dirname "$(g++ -print-file-name=libstdc++.so)")
  nvcc $flags $RW_NVCC_FLAGS $RW_LINEINFO $incs "$TDIR/driver.cu" libdeps.a -Xlinker -rpath,$gccdir -o driver || return 1
  nvcc -Xcompiler -H $flags $RW_NVCC_FLAGS $RW_LINEINFO $incs -c -o /dev/null "$TDIR/driver.cu" > hdr.log 2>&1
  bash "$TDIR/raft_h_proof.sh" hdr.log "$SRC" | tee h_proof.txt
}
t_cmd() { echo "$ART/driver"; }
