#ifndef YOSEMITE_H
#define YOSEMITE_H

#include <cstddef>
#include <cstdint>
#include <string>

typedef enum {
    YOSEMITE_SUCCESS = 0,
    YOSEMITE_ERROR = 1,
    YOSEMITE_NOT_IMPLEMENTED = 2,
    YOSEMITE_CUDA_MEMFREE_ZERO = 3
} YosemiteResult_t;


typedef enum {
    GPU_NO_PATCH = 0,
    GPU_PATCH_APP_METRIC = 1,
    GPU_PATCH_MEM_TRACE = 2,
    GPU_PATCH_HOT_ANALYSIS = 3,
    GPU_PATCH_UVM_ADVISOR = 4,
    GPU_PATCH_APP_ANALYSIS = 5,
    GPU_PATCH_APP_ANALYSIS_CPU = 6,
    GPU_PATCH_APP_ANALYSIS_NVBIT = 7,
    GPU_PATCH_TIME_HOTNESS_CPU = 8,
    GPU_PATCH_ROOFLINE_FLOPS_NVBIT = 9,
    GPU_PATCH_ROOFLINE_SIZE = 10,
    GPU_PATCH_HEATMAP_ANALYSIS = 11,
    GPU_PATCH_BLOCK_DIVERGENCE_ANALYSIS = 12,
    GPU_PATCH_PC_DEPENDENCY_ANALYSIS = 13,
} AccelProfPatchName_t;


typedef struct AccelProfOptions {
    AccelProfPatchName_t patch_name;
    std::string patch_file;
    bool sanitizer_callback_enabled = true;
    bool torch_prof_enabled = false;
    uint64_t grid_launch_id = 0;
    uint32_t sample_rate = 1;

    AccelProfOptions() = default;
    ~AccelProfOptions() = default;
} AccelProfOptions_t;


YosemiteResult_t yosemite_alloc_callback(uint64_t ptr, uint64_t size, int type, int device_id);

YosemiteResult_t yosemite_free_callback(uint64_t ptr, uint64_t size, int type, int device_id);

YosemiteResult_t yosemite_memcpy_callback(uint64_t dst, uint64_t src, uint64_t size, bool is_async, uint32_t direction, int device_id);

YosemiteResult_t yosemite_memset_callback(uint64_t dst, uint32_t size, int value, bool is_async, int device_id);

// T2 (design/host_memcpy_model.md): one host-side operation that orders or touches device
// memory outside any kernel. The collector sends these only when YOSEMITE_HB_HOST_MEMCPY=1;
// pc_dependency_analysis logs them to host_ops.json, every other tool ignores them.
typedef enum {
    YOSEMITE_HOST_MEMCPY = 0,         // src/dst/size (+ width/height/depth/pitches), is_async, direction
    YOSEMITE_HOST_MEMSET = 1,         // dst, width bytes x height rows at dst_pitch, is_async
    YOSEMITE_HOST_LAUNCH = 2,         // stream; flags = 1 if the launch was monitored (has a kernel_N.json)
    YOSEMITE_HOST_STREAM_CREATE = 3,  // stream; flags = cuStreamGetFlags, 0xffffffff if unknown
    YOSEMITE_HOST_STREAM_SYNC = 4,    // stream
    YOSEMITE_HOST_CTX_SYNC = 5,
    YOSEMITE_HOST_EVENT_RECORD = 6,   // event, stream
    YOSEMITE_HOST_STREAM_WAIT = 7,    // event, stream
    YOSEMITE_HOST_EVENT_SYNC = 8,     // event
    YOSEMITE_HOST_ALLOC = 9,          // pinned host memory: dst, size, flags
    YOSEMITE_HOST_FREE = 10,          // dst, size
} YosemiteHostOpKind_t;

typedef struct YosemiteHostOp {
    uint32_t kind = 0;
    uint64_t stream = 0;      // Sanitizer_StreamHandle of the op's (API) stream
    uint64_t stream_ptr = 0;  // its CUstream value (0 = NULL = the legacy default stream)
    uint64_t event = 0;       // CUevent
    uint32_t flags = 0;
    uint64_t src = 0, dst = 0, size = 0;
    uint64_t width = 0, height = 0, depth = 0, src_pitch = 0, dst_pitch = 0;
    uint32_t is_async = 0, direction = 0;   // direction: Sanitizer_MemcpyDirection
} YosemiteHostOp_t;

YosemiteResult_t yosemite_host_op_callback(const YosemiteHostOp_t& op);

YosemiteResult_t yosemite_kernel_start_callback(
    std::string kernel_name,
    int device_id,
    uint32_t grid_dim_x = 0,
    uint32_t grid_dim_y = 0,
    uint32_t grid_dim_z = 0,
    uint32_t block_dim_x = 0,
    uint32_t block_dim_y = 0,
    uint32_t block_dim_z = 0
);

YosemiteResult_t yosemite_kernel_end_callback(std::string kernel_name, int device_id);

YosemiteResult_t yosemite_gpu_data_analysis(void* data, uint64_t size);

YosemiteResult_t yosemite_init(AccelProfOptions_t& options);

YosemiteResult_t yosemite_terminate();

YosemiteResult_t yosemite_tensor_malloc_callback(uint64_t ptr, int64_t alloc_size,
                                int64_t total_allocated, int64_t total_reserved, int device_id);

YosemiteResult_t yosemite_tensor_free_callback(uint64_t ptr, int64_t alloc_size,
                                int64_t total_allocated, int64_t total_reserved, int device_id);

YosemiteResult_t yosemite_operator_start_callback(void* ctx, std::string op_name);

YosemiteResult_t yosemite_operator_end_callback(void* ctx, std::string op_name);

YosemiteResult_t yosemite_query_active_ranges(void* ranges, uint32_t limit, uint32_t* count);

YosemiteResult_t yosemite_query_active_tensors(void* ranges, uint32_t limit, uint32_t* count);


#endif // YOSEMITE_H
