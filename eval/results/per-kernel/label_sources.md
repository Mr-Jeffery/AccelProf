# Label sources (X13, step 4)

Quoted from the sources the binaries were built from. HeCBench: `6a8c46c4` (blobless clone `/home/fzheng4/x11-work/HeCBench`). ScoR: `~/AccelProf/ScoR/benchmarks`. Indigo3: `corpora/Indigo3Suite/generatedCodes/CUDA/...` (BeeGFS).
Tridiagonal labels: the agent's source-based proposal, adopted by Jeffery without review (2026-11-09).

## Indigo3 `init` kernels (one per code; BFS, CC, MIS, MST templates read, one code each)
```
===== Indigo3Suite/generatedCodes/CUDA/BFS-CUDA/BFS_CUDA_E_Data_IntType_ReadModifyWrite_NonPersist_Atomic_ExcessThreadsBug_NoLivelockBug_Determ_NoUninitializedBug_FieldBug_NoOverfl
45: 
46: static __global__ void init(const int src, data_type* const dist, data_type* const dist_n, const int size, const ECLgraph g, int* const wl1, int* const wlsize, int* const time)
47: {
48:   // initialize dist array
49:   const int v = threadIdx.x + blockIdx.x * ThreadsPerBlock;
50:   if (v < size) {
51:     const data_type temp = (v == src) ? 0 : maxval;
52:     dist_n[v] = temp;
53:     dist[v] = temp;
54:   }
55:   if (v < g.edges) {
56:     time[v] = 0;
57:   }
58:   // initialize worklist
59:   if (v == 0) {
===== Indigo3Suite/generatedCodes/CUDA/CC-CUDA/CC_CUDA_E_Data_IntType_ReadModifyWrite_NonPersist_Atomic_ExcessThreadsBug_NoLivelockBug_Determ_FieldBug_Init.cu lines 47 - 60
46: 
47: static __global__ void init(data_type* const label, data_type* const label_n, const ECLgraph g, int* const wl1, int* const wlsize)
48: {
49:   // initialize label array
50:   const int v = threadIdx.x + blockIdx.x * ThreadsPerBlock;
51:   if (v < g.nodes) {
52:     label_n[v] = v;
53:     label[v] = v;
54:     for (int i = g.nindex[v]; i < g.nindex[v + 1]; i++) {
55:       wl1[i] = i;
56:     }
57:   }
58:   if (v == 0) {
59:     *wlsize = g.edges;
60:   }
===== Indigo3Suite/generatedCodes/CUDA/MIS-CUDA/MIS_CUDA_E_Data_push_Determ_IntType_NonPersist_Atomic_Thread_FieldBug_ExcessThreadsBug_NoUninitializedBug.cu lines 46 - 59
45: 
46: static __global__ void init(const ECLgraph g, const int* const sp, data_type* const priority, flag_t* const status, flag_t* const status_n, flag_t* const lost, int* const wl1, 
47: {
48:   // initialize arrays
49:   const int v = threadIdx.x + blockIdx.x * ThreadsPerBlock;
50:   if (v < g.nodes)
51:   {
52:     priority[v] = hash(v + 712313887);
53:     status[v] = undecided;
54:     status_n[v] = undecided;
55:     lost[v] = 0;
56:   }
57:   if (v < g.edges)
58:   {
59:     // initialize worklist
===== Indigo3Suite/generatedCodes/CUDA/MST-CUDA/MST_CUDA_E_Data_Atomic_IntType_NonPersist_ExcessThreadsBug_FieldBug.cu lines 46 - 59
45: 
46: static __global__ void init(const ECLgraph g, data_type* const eweight, bool* const included, idx_type* const parent, idx_type* const minv, int* const wl1, idx_type* const wlsi
47: {
48:   const int v = threadIdx.x + blockIdx.x * ThreadsPerBlock;
49:   if (v < g.nodes) {
50:     //initially, each vertex is its own parent
51:     parent[v] = v;
52:     minv[v] = INT_MAX;
53: 
54:     const int beg = g.nindex[v];
55:     const int end = g.nindex[v + 1];
56:     for (int e = beg; e < end; e++) {
57:       const int n = g.nlist[e];
58:       // only in one direction
59:       if (n > v) {
```
Each thread writes `x[v]` (its own element) or its own adjacency range `wl1[nindex[v] .. nindex[v+1])`; `v == 0` alone writes `*wlsize`.

## ScoR (`#ifdef RACEY` blocks)
```
#### 1dconv/1dconv_kernel.cu:40-80
40:using namespace std;
41:#include "1dconv_kernel.cuh"
42:
43:__global__
44:void initKernel(float *filter, int filterSize, float *array, int arraySize, float *output)
45:{
46:    int bid  = blockIdx.x;
47:    int btid = threadIdx.x;
48:    int gtid = bid * blockDim.x + btid;
49:    
50:    int yid = gtid;
51:    while (yid < arraySize) {
52:        output[yid] = 0.0;
53:        yid += NTHREADS_TOT;
54:    }
55:}
56:
57:__global__
58:void convolveKernel(float *filter, int filterSize, float *array, int arraySize, float *output)
59:{
60:    int bid = blockIdx.x;
61:    int btid = threadIdx.x;
62:    int gtid = bid * blockDim.x + btid;
63:    
64:    int offset = 0;
65:    while(offset < arraySize * filterSize) {
66:        int filterIndex = (offset + gtid) % filterSize;
67:        int outputIndex = (offset + gtid) / filterSize; 
68:        if(outputIndex < arraySize) {
69:            int inputIndex = outputIndex - (filterIndex - filterSize / 2);
70:            if(inputIndex >= 0 && inputIndex < arraySize) {
71:#ifdef RACEY
72:                atomicAdd_block(&output[outputIndex], array[inputIndex] * filter[filterIndex]);
73:#else
74:                // Only this block's threads are writing to location
75:                if(btid >= filterIndex && blockDim.x - btid >= filterSize - filterIndex)
76:                    atomicAdd_block(&output[outputIndex], array[inputIndex] * filter[filterIndex]);
77:                else
78:                    atomicAdd(&output[outputIndex], array[inputIndex] * filter[filterIndex]);
79:#endif
80:            }
#### graph-coloring/gcol_kernel.cu:110-122
110:
111:        if(tid == 0) {
112:#ifdef RACEY
113:            *base = atomicAdd_block(&head[bid], NTHREADS);
114:#else
115:            *base = atomicAdd(&head[bid], NTHREADS);
116:#endif
117:        }
118:#ifdef RACEY
119:#else
120:        __syncthreads();
121:#endif
122:        my_base = *base;
#### graph-connectivity/gcon_kernel.cu:72-78
72:            graphComponents[tid + my_base] = tid + my_base;
73:        }
74:#ifdef RACEY
75:#else
76:        __syncthreads();
77:#endif
78:
#### matrix-multiplication/mm_kernel.cu:98-128
98:                do {
99:                    if(atomicCAS_block(&sh_lock, 0, 1) == 0) {
100:#ifdef RACEY
101:#else
102:                        __threadfence_block();
103:#endif
104:                        tempC += t;
105:#ifdef RACEY
106:#else
107:                        __threadfence_block();
108:#endif
109:                        atomicExch_block(&sh_lock, 0);
110:                        success = true;
111:                    }
112:                }while(!success);
113:            }
114:            __syncthreads();
115:            
116:            // Update the result array with value
117:            if(tid / WARP_SIZE == 0 && row < rA && i * WARP_SIZE + tid < cB) {
118:                bool successful = false;
119:                do {
120:#ifdef RACEY
121:                    // 2 races: One on gl_lock due to block atomic, other on C, due to block-scope locking
122:                    if(0 == atomicCAS_block((int*)&gl_lock[(i * WARP_SIZE + tid + row * cB) % NTHREADS], 0, 1)) {
123:                        __threadfence_block();
124:#else
125:                    if(0 == atomicCAS((int*)&gl_lock[(i * WARP_SIZE + tid + row * cB) % NTHREADS], 0, 1)) {
126:                        __threadfence();
127:#endif
128:                        C[i * WARP_SIZE + tid + row * cB] += tempC;__threadfence();
#### rule-110/r110_kernel.cu:79-122
79:    // Threadfence and mark complete
80:    if(isBorder()) {
81:#ifdef RACEY
82:        __threadfence_block();
83:#else
84:        __threadfence();
85:#endif
86:        atomicExch(&comp[tid], step);
87:    }
88:    else {
89:        __threadfence_block();
90:        atomicExch_block(&comp[tid], step);
91:    }
92:    
93:    // Use device scope for border neighbors, and block for non-border
94:    if(btid - 1 == 0 || btid == 0) {
95:        while(step != atomicAdd(&comp[(NBLOCKS * NTHREADS + tid - 1) % (NBLOCKS * NTHREADS)], 0));
96:        __threadfence();
97:    }
98:    else {
99:        while(step != atomicAdd_block(&comp[tid - 1], 0));
100:        __threadfence_block();
101:    }
102:    
103:    offset = 0;
104:    while(offset < size) {
105:        int ind = tid + offset;
106:        
107:        if(ind < size) {
108:            if(ind > 0)
109:                arr[ind] = copy[ind - 1];
110:            else
111:                arr[ind] = 0;
112:        }
113:        offset += NBLOCKS * NTHREADS;
114:    }
115:    
116:    if(btid + 1 == NTHREADS || btid + 1 == NTHREADS - 1) {
117:#ifdef RACEY
118:        while(step != atomicAdd_block(&comp[(NBLOCKS * NTHREADS + tid + 1) % (NBLOCKS * NTHREADS)], 0));
119:#else
120:        while(step != atomicAdd(&comp[(NBLOCKS * NTHREADS + tid + 1) % (NBLOCKS * NTHREADS)], 0));
121:#endif
122:        __threadfence();
#### reduction/red_kernel.cu:76-82
76:        if (tid >= 32) {
77:            sdata[tid] = mySum + sdata[tid +  64];
78:#ifdef RACEY
79:#else
80:            __threadfence_block();
81:#endif
82:            atomicExch_block(&lock[tid], 1);
#### reduction/red_kernel.cu:178-185
178:
179:        // wait until all outstanding memory instructions in this thread are finished
180:#ifdef RACEY
181:        __threadfence_block();
182:#else
183:        __threadfence();
184:#endif
185:        // Thread 0 takes a ticket
#### uts/uts_kernel.cu:228-262
228:        parent.param[CHILDREN] = 0;
229:        SYNC_WARP;
230:#ifdef RACEY
231:        while(wtid == 0 && atomicCAS_block(&stealStackStats[blk].locked, 0, 1) != 0);
232:#else
233:        while(wtid == 0 && atomicCAS(&stealStackStats[blk].locked, 0, 1) != 0);
234:#endif
235:        __threadfence();
236:        SYNC_WARP;
237:        if(atomicAdd((int*)&stealStackStats[blk].workAvail, 0) > wtid) {
238:            *(unsigned int *)(parent.param) = atomicAdd((int *)&stealStacks[
239:                (stealStackStats[blk].top + wtid) % MAXSTACKDEPTH + MAXSTACKDEPTH * blk].param, 0);
240:            if(wtid == 0) {
241:                stealStackStats[blk].top = (stealStackStats[blk].top + 
242:                    min(WARP_SIZE, atomicAdd((int*)&stealStackStats[blk].workAvail, 0)))
243:                    % MAXSTACKDEPTH + MAXSTACKDEPTH * blk;
244:              
245:                int val = atomicSub((int*)&stealStackStats[blk].workAvail, WARP_SIZE);
246:                if(val - WARP_SIZE < 0)
247:#ifdef RACEY
248:                    atomicExch_block((int*)&stealStackStats[blk].workAvail, 0);
249:#else
250:                    atomicExch((int*)&stealStackStats[blk].workAvail, 0);
251:#endif
252:            }
253:        }
254:        SYNC_WARP;
255:        if(wtid == 0) {
256:            __threadfence();
257:#ifdef RACEY
258:            atomicExch_block(&stealStackStats[blk].locked, 0);
259:#else
260:            atomicExch(&stealStackStats[blk].locked, 0);
261:#endif
262:        }

```
1dconv: the RACEY block (lines 71-79) is inside `convolveKernel` (starts :57); `initKernel` (:43-55) has none -> `initKernel` race-free, `convolveKernel` racy. graph-coloring / graph-connectivity: RACEY blocks in all three kernels (grep: gcol_kernel.cu:112,118,183,189,256,262; gcon_kernel.cu:74,148,176,226,252).

## HeCBench 6a8c46c4
### knn `cuComputeDistanceGlobal` (`main.cu`) - racy; `cuInsertionSort`, `cuParallelSqrt` race-free
```
  __shared__ int begin_A;
  __shared__ int begin_B;
  begin_A = BLOCK_DIM * blockIdx.y;
  begin_B = BLOCK_DIM * blockIdx.x;
  step_A = BLOCK_DIM * wA;
  step_B = BLOCK_DIM * wB;
  end_A = begin_A + (dim - 1) * wA;
```
(`cuInsertionSort`: `p_dist = dist + xIndex; p_ind = ind + xIndex`, every access `p_dist[k*width]` is in the thread's own column; `cuParallelSqrt`: `dist[yIndex*width+xIndex] = sqrt(dist[yIndex*width+xIndex])`, no shared memory.)

### atomicCAS `kernels.h` - every overload reads `*address` plainly, then `atomicCAS` on the same address
```

// int64 atomic_min
__device__ __forceinline__
long long atomic_min(long long *address, long long val)
{
  long long ret = *address;
  while(val < ret)
  {
    long long old = ret;
    if((ret = atomicCAS((unsigned long long *)address, (unsigned long long)old, (unsigned long long)val)) == old)
      break;
  }
  return ret;
}

// uint64 atomic_min
__device__ __forceinline__
unsigned long long atomic_min(unsigned long long *address, unsigned long long val)
{
  unsigned long long ret = *address;
  while(val < ret)
  {
    unsigned long long old = ret;
    if((ret = atomicCAS(address, old, val)) == old)
      break;
  }
  return ret;
}

// int64 atomic add
__device__ __forceinline__
long long atomic_add(long long *address, long long val)
{
  long long old, newdbl, ret = *address;
  do {
    old = ret;
    newdbl = old+val;
  } while((ret = (long long)atomicCAS((unsigned long long*)address, (unsigned long long)old, (unsigned long long)newdbl)) != old);
  return ret;
}

// int64 atomic_max
__device__ __forceinline__
long long atomic_max(long long *address, long long val)
{
  long long ret = *address;
  while(val > ret)
  {
    long long old = ret;
    if((ret = (long long)atomicCAS((unsigned long long *)address, (unsigned long long)old, (unsigned long long)val)) == old)
      break;
  }
  return ret;
}

// uint64 atomic_max
__device__ __forceinline__
unsigned long long atomic_max(unsigned long long *address, unsigned long long val)
{
  unsigned long long ret = *address;
  while(val > ret)
  {
    unsigned long long old = ret;
    if((ret = atomicCAS(address, old, val)) == old)
      break;
  }
  return ret;
}

// uint64 atomic add
__device__ __forceinline__
unsigned long long
```

### expdist `kernel.h`
```
    19	template <int tile_size, int stride, typename T>
    20	__device__ __forceinline__
    21	void fill_shared_mem_tiled_1D(
    22	  T (&sh_mem)[tile_size*stride], 
    23	  const T *__restrict__ d_mem,
    24	  int sh_offset, int d_offset)
    25	{
    26	  #pragma unroll
    27	  for (int ti=0; ti<tile_size; ti++) {
    28	    sh_mem[sh_offset+ti*stride] = d_mem[d_offset+ti*stride];
    29	  }
    30	}
    41	template<typename T, int dim>
    42	__device__ __forceinline__
    43	void distance_tiled(
    44	  const T *__restrict__ A, 
    45	  const T *__restrict__ B,
    46	  int m, int n, 
    47	  const T *__restrict__ scale_A,
    48	  const T *__restrict__ scale_B,
    49	  T *__restrict__ cross_term)
    50	{
    51	  int tx = threadIdx.x;
    52	  int ty = threadIdx.y;
    53	  int i = tx + blockIdx.x * block_size_x * tile_size_x;
    54	  int j = ty + blockIdx.y * block_size_y * tile_size_y;
    55	
    56	  __shared__ T sh_A[dim][block_size_x*tile_size_x];
    57	  __shared__ T sh_B[dim][block_size_y*tile_size_y];
    58	  __shared__ T sh_scale_A[block_size_x*tile_size_x];
    59	  __shared__ T sh_scale_B[block_size_y*tile_size_y];
    60	  __shared__ T sum;
    62	  if (tx == 0 && ty == 0) sum = 0;
    63	
    64	  #pragma unroll
    65	  for (int d=0; d<dim; d++) {
    66	    fill_shared_mem_tiled_1D<tile_size_x, block_size_x>(sh_A[d], A+d*m, tx, i);
    67	    fill_shared_mem_tiled_1D<tile_size_y, block_size_y>(sh_B[d], B+d*n, ty, j);
    68	  }
    69	  fill_shared_mem_tiled_1D<tile_size_x, block_size_x>(sh_scale_A, scale_A, tx, i);
    70	  fill_shared_mem_tiled_1D<tile_size_y, block_size_y>(sh_scale_B, scale_B, ty, j);
    84	          dist_ij += (sh_A[d][tx+ti*block_size_x]-sh_B[d][ty+tj*block_size_y])*
    85	                     (sh_A[d][tx+ti*block_size_x]-sh_B[d][ty+tj*block_size_y]);
    86	        }
    87	        s_cross_term += exp(-dist_ij/(sh_scale_A[tx+ti*block_size_x] + sh_scale_B[ty+tj*block_size_y]));
    88	      }
    89	    }
    90	  }
    91	
    92	  atomicAdd(&sum, s_cross_term);
    93	  __syncthreads();
    94	
    95	  //write back the per-thread block partial cross term
    96	  if (tx == 0 && ty == 0) {
    97	    cross_term[blockIdx.y*gridDim.x+blockIdx.x] = sum;
    98	  }
    99	}
   100	
   101	template<typename T>
   102	__global__ 
   103	void distance(
   104	  const T *__restrict__ A,
   105	  const T *__restrict__ B,
   106	  int m, int n,
   107	  const T *__restrict__ scale_A,
   108	  const T *__restrict__ scale_B, 
   109	        T *__restrict__ cross_term)
   110	{
   111	  //2-dimensional with T precision
   112	  distance_tiled<T, 2>(A, B, m, n, scale_A, scale_B, cross_term);
   113	}
   124	template<typename T>
   125	__global__
   126	void reduce_cross_term(
   127	        T *__restrict__ output,
   128	  const T *__restrict__ cross_term,
   129	  int m, int n, int nblocks)
   130	{
   131	  int tx = threadIdx.x;
   132	
   133	  __shared__ T sum;
   134	
   135	  if (tx == 0) sum = 0;
   136	  __syncthreads();
   137	
   138	  T s_cross_term = 0;
   139	  for (int i=tx; i<nblocks; i+=reduce_block_size)
   140	    s_cross_term += cross_term[i];
   141	
   142	  atomicAdd(&sum, s_cross_term);
   143	
   144	  __syncthreads();
   145	
   146	  if (tx == 0) output[0] = sum;
   147	}

```
`distance<T>` -> `distance_tiled<T,2>` -> `fill_shared_mem_tiled_1D` (:28 writes `sh_mem`) then reads of `sh_A`/`sh_scale_A` at :84-87 with no `__syncthreads()` between: racy. `reduce_cross_term<T>`: `sum` set by thread 0 then `__syncthreads()` (:135-136); private accumulation; `atomicAdd(&sum, s)` then `__syncthreads()` (:142-144) before thread 0 reads `sum` (:146): race-free.

### tridiagonal (proposal)
`cyclic_kernels.cu` (cat -n numbering = file lines):
```
    66	    __syncthreads();
    67	
    76	#ifndef NATIVE_DIVIDE
    77	        float tmp = a[i] / b[i-delta];
    78	#else
    79	        float tmp = __fdiv_rn(a[i], b[i-delta]);
    80	#endif
    81	        b[i] = b[i] - c[i-delta] * tmp;
    82	        d[i] = d[i] - d[i-delta] * tmp;
    83	        a[i] = -a[i-delta] * tmp;
    84	        c[i] = 0;      
    85	      }
    86	      else
    87	      {
    88	#ifndef NATIVE_DIVIDE
    89	        float tmp1 = a[i] / b[i-delta];
    90	        float tmp2 = c[i] / b[i+delta];
    91	#else
    92	        float tmp1 = __fdiv_rn(a[i], b[i-delta]);
    93	        float tmp2 = __fdiv_rn(c[i], b[i+delta]);
    94	#endif
    95	        b[i] = b[i] - c[i-delta] * tmp1 - a[i+delta] * tmp2;
    96	        d[i] = d[i] - d[i-delta] * tmp1 - d[i+delta] * tmp2;
    97	        a[i] = -a[i-delta] * tmp1;
    98	        c[i] = -c[i+delta] * tmp2;
    99	      }
   100	    }
   101	    thid_num >>= 1;
   102	  }
   103	
   104	  if (thid < 2)
   105	  {
   106	    int addr1 = stride - 1;
   107	    int addr2 = (stride << 1) - 1;
   108	    float tmp3 = b[addr2] * b[addr1] - c[addr1] * a[addr2];
   109	#ifndef NATIVE_DIVIDE
   110	    x[addr1] = (b[addr2] * d[addr1] - c[addr1] * d[addr2]) / tmp3;
   111	    x[addr2] = (d[addr2] * b[addr1] - d[addr1] * a[addr2]) / tmp3;
   112	#else
   113	    x[addr1] = __fdiv_rn((b[addr2] * d[addr1] - c[addr1] * d[addr2]), tmp3);
   114	    x[addr2] = __fdiv_rn((d[addr2] * b[addr1] - d[addr1] * a[addr2]), tmp3);
   115	#endif
   116	  }
   117	
   118	  // backward substitution
   119	  thid_num = 2;
   195	    if (thid < thid_num)
   196	    { 
   197	      int i = stride * thid + stride - 1;
   198	      int iRight = i+delta;
   199	      iRight = iRight & (system_size-1);
   205	      float tmp2 = __fdiv_rn(c[i], b[iRight]);
   206	#endif
   207	      b[i] = b[i] - c[i-delta] * tmp1 - a[iRight] * tmp2;
   208	      d[i] = d[i] - d[i-delta] * tmp1 - d[iRight] * tmp2;
   209	      a[i] = -a[i-delta] * tmp1;
   210	      c[i] = -c[iRight]  * tmp2;
   211	    }
   212	
   213	    thid_num >>= 1;
   214	  }
   215	
   216	  if (thid < 2)
   217	  {
   218	    int addr1 = stride - 1;
   219	    int addr2 = (stride << 1) - 1;
   220	    float tmp3 = b[addr2] * b[addr1] - c[addr1] * a[addr2];
   221	#ifndef NATIVE_DIVIDE
   222	    x[addr1] = (b[addr2] * d[addr1] - c[addr1] * d[addr2]) / tmp3;
   223	    x[addr2] = (d[addr2] * b[addr1] - d[addr1] * a[addr2]) / tmp3;
   224	#else
   225	    x[addr1] = __fdiv_rn((b[addr2] * d[addr1] - c[addr1] * d[addr2]), tmp3);
   226	    x[addr2] = __fdiv_rn((d[addr2] * b[addr1] - d[addr1] * a[addr2]), tmp3);
   227	#endif
   228	  }
   229	
```
`cyclic_small_systems_kernel` / `cyclic_branch_free_kernel`: the last forward-elimination iteration writes `b[i], d[i], a[i], c[i]` (:81-98 / :207-210) by threads `thid < thid_num` (2 threads in the last iteration), then `thid < 2` read `b[addr1], b[addr2], c[addr1], a[addr2], d[...]` at :108-116 / :220-228 with no `__syncthreads()` between the loop end and the read (the barrier is at the top of each iteration, :66 / :191). `pcr_*`: barriers at `pcr_kernels.cu` :54, :100, :108, :125 (small) and :160, :186, :194, :211 (branch free). `sweep_*`: no shared memory, one thread per system (`sweep_kernels.cu` :20-106, :117-, :269-357). `transpose` (:364-399): tile, `__syncthreads()` :395. Launched under the default arguments: pcr x2, cyclic x2, `sweep_small_systems_global_kernel`, `transpose` (`main.cu`: `useLmem`, `useVec4` default false).
