/* X13: LD_PRELOAD shim logging cudaMalloc results ("[x13-malloc] ptr size") to stderr, to name the allocation
   (e.g. bfs's d_over) that owns a hot segment. Passive: forwards to the real cudaMalloc. */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stddef.h>
typedef int (*malloc_fn)(void**, size_t);
int cudaMalloc(void** p, size_t n) {
    static malloc_fn real = 0;
    if (!real) real = (malloc_fn)dlsym(RTLD_NEXT, "cudaMalloc");
    int r = real(p, n);
    fprintf(stderr, "[x13-malloc] %p %zu\n", p ? *p : 0, n);
    return r;
}
