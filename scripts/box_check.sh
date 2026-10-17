#!/bin/bash
# Run ON a freshly rented box (read-only towards everything except a scratch folder you name). Prints the real limits
# and, optionally, a 1-core dgemm and a QE validation run. Nothing here is project-specific: the validation input and
# its expected energy come from the project (a finished production input, only pseudo_dir/outdir changed).
#
# usage: bash box_check.sh                                  # limits only
#        bash box_check.sh --dgemm                          # + 1-core numpy dgemm GFLOPS (needs python3 + numpy)
#        bash box_check.sh --validate PW_X INPUT EXPECTED_RY NP [NK]   # + run pw.x, compare the last '!' energy
# Compare the numbers with the previous box (vm-campaign.md §2) BEFORE moving any production job here.
set -u
echo "== CPU"; lscpu | grep -E "Model name|Socket|Core\(s\) per socket|Thread\(s\) per core|^CPU\(s\)|NUMA node[0-9]" || true
echo "thread siblings of cpu0: $(cat /sys/devices/system/cpu/cpu0/topology/thread_siblings_list 2>/dev/null)"
echo "nproc: $(nproc)   physical cores: $(lscpu -p=core,socket 2>/dev/null | grep -v '^#' | sort -u | wc -l)"
echo "== cgroup limits"
echo "cpu.max: $(cat /sys/fs/cgroup/cpu.max 2>/dev/null || echo n/a)   (quota/period = usable CPUs)"
echo "memory.max: $(cat /sys/fs/cgroup/memory.max 2>/dev/null || echo n/a)"
grep -E "oom_kill" /sys/fs/cgroup/memory.events 2>/dev/null || true
echo "== memory and disk"; free -g | head -2; df -h / /dev/shm 2>/dev/null
echo "== GPUs (useless for CPU QE; listed only so nobody pays extra for them)"; nvidia-smi -L 2>/dev/null || echo none
if [ "${1:-}" = "--dgemm" ]; then
  echo "== 1-core dgemm"
  OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python3 - <<'EOF'
import time
import numpy as np
n = 2000; a = np.random.rand(n, n); b = np.random.rand(n, n); a @ b
t = time.time(); r = 3
for _ in range(r):
    a @ b
dt = (time.time() - t) / r
print(f"dgemm {n}: {2 * n**3 / dt / 1e9:.1f} GFLOPS on one core")
EOF
fi
if [ "${1:-}" = "--validate" ]; then
  PW=$2; IN=$3; EXP=$4; NP=$5; NK=${6:-1}
  export OMPI_ALLOW_RUN_AS_ROOT=1 OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
         HWLOC_COMPONENTS=-gl,-opencl,-cuda,-nvml
  OUT="${IN%.in}.validate.out"
  echo "== validation: $PW -np $NP -nk $NK -in $IN > $OUT"
  mpirun --bind-to none -np "$NP" "$PW" -nk "$NK" -in "$IN" > "$OUT" 2> "${OUT%.out}.err" < /dev/null
  GOT=$(awk '/^!/ {e=$5} END {print e}' "$OUT")
  echo "expected $EXP  got $GOT"
  if [ "$GOT" = "$EXP" ]; then echo "VALIDATION PASS (every printed digit)"; else echo "VALIDATION FAIL"; exit 1; fi
fi
