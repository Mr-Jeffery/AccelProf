// T21a kokkos-5 driver: scalar Kokkos::parallel_reduce on the CUDA backend (RangePolicy, n = 1000, double sum).
// Goes through ParallelReduce<..., RangePolicy, Cuda> -> cuda_single_inter_block_reduce_scan ->
// CudaReductionsFunctor<FunctorType, void, false, false>::scalar_intra_warp_reduction (Kokkos_Cuda_ReduceScan.hpp).
// A functor (not KOKKOS_LAMBDA) so no extended-lambda flag is needed; the dispatch is the same.
#include <Kokkos_Core.hpp>
#include <cstdio>

struct RwSumFunctor {
  KOKKOS_INLINE_FUNCTION void operator()(const int i, double& u) const { u += i; }
};

int main(int argc, char** argv) {
  Kokkos::initialize(argc, argv);
  int rc = 0;
  {
    const int n = 1000;
    double s    = 0.0;
    Kokkos::parallel_reduce("rw_sum", Kokkos::RangePolicy<Kokkos::Cuda>(0, n), RwSumFunctor(), s);
    Kokkos::fence();
    const double ref = 0.5 * n * (n - 1);
    rc               = (s == ref) ? 0 : 1;
    std::printf("kokkos-5 driver: n=%d sum=%.1f expected=%.1f %s\n", n, s, ref, rc ? "MISMATCH" : "OK");
  }
  Kokkos::finalize();
  return rc;
}
