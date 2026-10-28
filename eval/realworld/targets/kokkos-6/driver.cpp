/*
//@HEADER
// ************************************************************************
//
//                        Kokkos v. 3.0
//       Copyright (2020) National Technology & Engineering
//               Solutions of Sandia, LLC (NTESS).
//
// Under the terms of Contract DE-NA0003525 with NTESS,
// the U.S. Government retains certain rights in this software.
//
// Redistribution and use in source and binary forms, with or without
// modification, are permitted provided that the following conditions are
// met:
//
// 1. Redistributions of source code must retain the above copyright
// notice, this list of conditions and the following disclaimer.
//
// 2. Redistributions in binary form must reproduce the above copyright
// notice, this list of conditions and the following disclaimer in the
// documentation and/or other materials provided with the distribution.
//
// 3. Neither the name of the Corporation nor the names of the
// contributors may be used to endorse or promote products derived from
// this software without specific prior written permission.
//
// THIS SOFTWARE IS PROVIDED BY NTESS "AS IS" AND ANY
// EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
// IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
// PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL NTESS OR THE
// CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
// EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
// PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
// PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
// LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
// NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
// SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
//
// Questions? Contact Christian R. Trott (crtrott@sandia.gov)
//
// ************************************************************************
//@HEADER
*/

// (licence header of core/unit_test/TestTeam.hpp at 71761882dc, kept because the test body below is pasted from that file)
// T21a kokkos-6 driver: the unit test TestRepeatedTeamReduce that the fix commit 71761882d adds to core/unit_test/TestTeam.hpp
// (it does not exist at the parent af6523318), pasted verbatim into a stand-alone main, with ONLY these changes:
//   - ncol (league size)            1500 -> 8
//   - outer repetitions (it loop)    100 -> 1
//   - gtest ASSERT_EQ(bad, 0) << ... replaced by a printed check (no gtest in this driver)
// Everything else (functor, nlev = 129, 10 x 2 team reductions per team, team size = recommended - 1) is unchanged.
// Racing code: Kokkos::Impl::cuda_inter_warp_reduction (core/src/Cuda/Kokkos_Cuda_ReduceScan.hpp) via the team parallel_reduce.
#include <Kokkos_Core.hpp>
#include <cstdio>

static int rw_bad_total = 0;

namespace Test {
namespace {
template <typename ExecutionSpace>
struct TestRepeatedTeamReduce {
  static constexpr int ncol = 8;  // nothing special, just some work   [T21a: 1500 -> 8]

  KOKKOS_FUNCTION void operator()(
      const typename Kokkos::TeamPolicy<ExecutionSpace>::member_type &team)
      const {
    // non-divisible by power of two to make triggering problems easier
    constexpr int nlev = 129;
    constexpr auto pi  = Kokkos::numbers::pi;
    double b           = 0.;
    for (int ri = 0; ri < 10; ++ri) {
      // The contributions here must be sufficiently complex, simply adding ones
      // wasn't enough to trigger the bug.
      const auto g1 = [&](const int k, double &acc) {
        acc += Kokkos::cos(pi * double(k) / nlev);
      };
      const auto g2 = [&](const int k, double &acc) {
        acc += Kokkos::sin(pi * double(k) / nlev);
      };
      double a1, a2;
      Kokkos::parallel_reduce(Kokkos::TeamThreadRange(team, nlev), g1, a1);
      Kokkos::parallel_reduce(Kokkos::TeamThreadRange(team, nlev), g2, a2);
      b += a1;
      b += a2;
    }
    const auto h = [&]() {
      const auto col = team.league_rank();
      v(col)         = b + col;
    };
    Kokkos::single(Kokkos::PerTeam(team), h);
  }

  KOKKOS_FUNCTION void operator()(const int i, int &bad) const {
    if (v(i) != v(0) + i) {
      ++bad;
      KOKKOS_IMPL_DO_NOT_USE_PRINTF("Failing at %d!\n", i);
    }
  }

  TestRepeatedTeamReduce() : v("v", ncol) { test(); }

  void test() {
    int team_size_recommended =
        Kokkos::TeamPolicy<ExecutionSpace>(1, 1).team_size_recommended(
            *this, Kokkos::ParallelForTag());
    // Choose a non-recommened (non-power of two for GPUs) team size
    int team_size = team_size_recommended > 1 ? team_size_recommended - 1 : 1;
    std::printf("kokkos-6 driver: league=%d team_size=%d (recommended %d)\n", ncol, team_size, team_size_recommended);

    // The failure was non-deterministic so run the test a bunch of times
    for (int it = 0; it < 1; ++it) {  // [T21a: 100 -> 1]
      Kokkos::parallel_for(
          Kokkos::TeamPolicy<ExecutionSpace>(ncol, team_size, 1), *this);

      int bad = 0;
      Kokkos::parallel_reduce(Kokkos::RangePolicy<ExecutionSpace>(0, ncol),
                              *this, bad);
      if (bad != 0) {  // [T21a: was ASSERT_EQ(bad, 0) << " Failing in iteration " << it;]
        std::printf("kokkos-6 driver: Failing in iteration %d, bad=%d\n", it, bad);
        rw_bad_total += bad;
      }
    }
  }

  Kokkos::View<double *, ExecutionSpace> v;
};

}  // namespace
}  // namespace Test

int main(int argc, char **argv) {
  Kokkos::initialize(argc, argv);
  {
    Test::TestRepeatedTeamReduce<Kokkos::Cuda>();
    std::printf("kokkos-6 driver: done, columns inconsistent: %d (nonzero is the symptom of the race, not a harness failure)\n", rw_bad_total);
  }
  Kokkos::finalize();
  return 0;
}
