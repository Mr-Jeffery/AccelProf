/* X13: LD_PRELOAD shim logging cudaMalloc results ("ptr size") to the file $X13_MALLOC_LOG (accelprof sends the
   application's stderr to /dev/null), to name the allocation (e.g. bfs's d_over) that owns a hot segment.
   Passive: forwards to the real cudaMalloc. */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <stddef.h>
typedef int (*malloc_fn)(void**, size_t);
int cudaMalloc(void** p, size_t n) {
    static malloc_fn real = 0;
    if (!real) real = (malloc_fn)dlsym(RTLD_NEXT, "cudaMalloc");
    int r = real(p, n);
    const char* path = getenv("X13_MALLOC_LOG");
    if (path) {
        FILE* f = fopen(path, "a");
        if (f) { fprintf(f, "%p %zu\n", p ? *p : 0, n); fclose(f); }
    }
    return r;
}
