#!/usr/bin/env python3
"""X9 harness: stand-in for `/usr/bin/time -v -o FILE cmd ...` on nodes without GNU time (a5000ada, some `normal`
nodes). Runs cmd, writes the two lines the harness reads ("Elapsed (wall clock) time" in seconds and "Maximum resident
set size (kbytes)", the peak RSS of the largest waited-for descendant, getrusage(RUSAGE_CHILDREN).ru_maxrss as GNU time
reports it) and exits with cmd's exit code.
usage: x9_timev.py -o FILE cmd [args...]"""
import resource, subprocess, sys, time
assert sys.argv[1] == "-o"
out, cmd = sys.argv[2], sys.argv[3:]
t0 = time.time()
rc = subprocess.call(cmd)
ru = resource.getrusage(resource.RUSAGE_CHILDREN)
with open(out, "w") as f:
    f.write(f"\tCommand being timed: \"{' '.join(cmd)}\"\n\tElapsed (wall clock) time (s): {time.time() - t0:.1f}\n"
            f"\tMaximum resident set size (kbytes): {ru.ru_maxrss}\n\tExit status: {rc}\n\t(x9_timev.py stand-in)\n")
sys.exit(rc)
