/* X13: static launcher standing in for the application binary: accelprof runs the application as
   `LD_PRELOAD=<collector> ./app`, which replaces any LD_PRELOAD of ours; this launcher (static, so the collector's
   preload does not touch it) re-executes the real binary ($X13_REAL_EXE) with $X13_PRELOAD (malloc_log.so) added in
   front of the collector in LD_PRELOAD. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
int main(int argc, char** argv) {
    const char* real = getenv("X13_REAL_EXE");
    const char* pre = getenv("X13_PRELOAD");
    if (!real || !pre) { fprintf(stderr, "exec_wrap: X13_REAL_EXE / X13_PRELOAD unset\n"); return 127; }
    const char* old = getenv("LD_PRELOAD");
    char* v = malloc(strlen(pre) + (old ? strlen(old) : 0) + 2);
    sprintf(v, "%s%s%s", pre, old ? ":" : "", old ? old : "");
    setenv("LD_PRELOAD", v, 1);
    argv[0] = (char*)real;
    execv(real, argv);
    perror("exec_wrap: execv");
    return 127;
}
