// T21a ginkgo-5 driver: Ginkgo's range-minimum-query lookup builders on the CUDA executor, the call sequence of the in-tree test
// test/components/range_minimum_query_kernels.cpp (ComputeLookupSmallAndLargeIsEquivalentToRef) for the single size 1025 (record:
// "use only size 1025 or 10000"), but with the CPU reference replaced by a host brute force written here (the reference backend is
// not built in this route).  The kernels under test are the revision's own gko::kernels::cuda::range_minimum_query::
// compute_lookup_small / compute_lookup_large (common/unified/components/range_minimum_query_kernels.cpp compiled as CUDA by the
// project's own build rules); this file only creates the executor, the arrays and calls them.  Only API that exists identically at
// both revisions is used (the two revisions differ in that one .cpp only).
#include <algorithm>
#include <cstdio>
#include <limits>
#include <random>
#include <vector>

#include <cuda_runtime_api.h>

#include <ginkgo/core/base/array.hpp>
#include <ginkgo/core/base/executor.hpp>

#include "core/components/bit_packed_storage.hpp"
#include "core/components/range_minimum_query.hpp"
#include "core/components/range_minimum_query_kernels.hpp"

int main()
{
    using index_type = gko::int32;
    using word_type = std::make_unsigned_t<index_type>;
    using block_argmin_storage_type =
        gko::kernels::cuda::range_minimum_query::block_argmin_storage_type<index_type>;
    using superblock_storage_type = gko::range_minimum_query_superblocks<index_type>;
    constexpr int block_size = gko::kernels::cuda::range_minimum_query::small_block_size;
    constexpr int block_argmin_num_bits = gko::ceil_log2_constexpr(block_size);
    const index_type size = 1025;

    auto ref = gko::ReferenceExecutor::create();
    auto exec = gko::CudaExecutor::create(0, ref);

    // random values, as in the test
    std::default_random_engine rng{19654};
    std::uniform_int_distribution<index_type> dist{0, std::numeric_limits<index_type>::max()};
    std::vector<index_type> hvalues(size);
    for (auto& v : hvalues) {
        v = dist(rng);
    }
    gko::array<index_type> values{ref, hvalues.begin(), hvalues.end()};
    gko::array<index_type> dvalues{exec, values};

    const auto num_blocks = static_cast<gko::size_type>(gko::ceildiv(size, block_size));
    gko::array<index_type> dblock_min{exec, num_blocks};
    const auto block_argmin_storage_size = static_cast<gko::size_type>(
        block_argmin_storage_type::storage_size(num_blocks, block_argmin_num_bits));
    gko::array<gko::uint32> dblock_argmin_storage{exec, block_argmin_storage_size};
    cudaMemset(dblock_argmin_storage.get_data(), 0, block_argmin_storage_size * sizeof(gko::uint32));
    block_argmin_storage_type dblock_argmin{dblock_argmin_storage.get_data(), block_argmin_num_bits,
                                            static_cast<index_type>(num_blocks)};
    gko::array<gko::uint16> dblock_type{exec, num_blocks};

    std::printf("ginkgo-5 driver: size=%d small_block_size=%d num_blocks=%zu\n", static_cast<int>(size), block_size,
                static_cast<size_t>(num_blocks));
    gko::kernels::cuda::range_minimum_query::compute_lookup_small(
        exec, dvalues.get_const_data(), size, dblock_argmin, dblock_min.get_data(), dblock_type.get_data());

    // superblocks for the large lookup
    const auto superblock_storage_size =
        static_cast<gko::size_type>(superblock_storage_type::compute_storage_size(num_blocks));
    gko::array<word_type> dsuperblock_storage{exec, superblock_storage_size};
    cudaMemset(dsuperblock_storage.get_data(), 0, superblock_storage_size * sizeof(word_type));
    superblock_storage_type dsuperblocks{dblock_min.get_const_data(), dsuperblock_storage.get_data(),
                                         static_cast<index_type>(num_blocks)};
    gko::kernels::cuda::range_minimum_query::compute_lookup_large(
        exec, dblock_min.get_const_data(), static_cast<index_type>(num_blocks), dsuperblocks);

    // bring everything back to the host and compare with a brute-force computation
    gko::array<index_type> block_min{ref, dblock_min};
    gko::array<gko::uint32> block_argmin_storage{ref, dblock_argmin_storage};
    gko::array<word_type> superblock_storage{ref, dsuperblock_storage};
    block_argmin_storage_type block_argmin{block_argmin_storage.get_data(), block_argmin_num_bits,
                                           static_cast<index_type>(num_blocks)};
    superblock_storage_type superblocks{block_min.get_const_data(), superblock_storage.get_data(),
                                        static_cast<index_type>(num_blocks)};

    int bad_min = 0, bad_argmin = 0, bad_super = 0;
    for (gko::size_type b = 0; b < num_blocks; b++) {
        int argmin = 0;
        index_type local[block_size];
        for (int j = 0; j < block_size; j++) {
            local[j] = b * block_size + j < size ? hvalues[b * block_size + j] : std::numeric_limits<index_type>::max();
            if (local[j] < local[argmin]) {
                argmin = j;
            }
        }
        bad_min += block_min.get_const_data()[b] != local[argmin];
        bad_argmin += static_cast<int>(block_argmin.get(b)) != argmin;
    }
    const auto num_levels = superblocks.num_levels();
    for (int level = 0; level < num_levels; level++) {
        const auto bs = superblock_storage_type::block_size_for_level(level);
        for (index_type i = 0; i < static_cast<index_type>(num_blocks); i++) {
            const auto last = std::min<index_type>(i + bs, static_cast<index_type>(num_blocks));
            index_type best = i;
            for (index_type k = i; k < last; k++) {
                if (block_min.get_const_data()[k] < block_min.get_const_data()[best]) {
                    best = k;
                }
            }
            bad_super += (i + superblocks.block_argmin(level, i)) != best;
        }
    }
    std::printf("ginkgo-5 driver: lookup_small block_min mismatches %d, block_argmin mismatches %d (of %zu blocks); "
                "lookup_large mismatches %d over %d levels\n",
                bad_min, bad_argmin, static_cast<size_t>(num_blocks), bad_super, static_cast<int>(num_levels));
    std::printf("ginkgo-5 driver: done (nonzero argmin/large mismatches are the symptom of the race, not a harness failure)\n");
    return 0;
}
