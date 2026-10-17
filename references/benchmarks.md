# Measured benchmarks: rented machines, workloads and parallel layouts

Contents: 1 Units · 2 The machines · 3 Same-input speed comparisons · 4 Parallel-layout experiments · 5 What the campaigns ran · 6 Rules that held · 7 Benchmark your own box and campaign

Every number here was measured during real campaigns between 22 Sep and 10 Oct 2026, in three projects described in `case-studies.md`: **A** (QE 7.3.1 built from source with gfortran -O3, OpenBLAS, ScaLAPACK, FFTW3 and Open MPI 4.1.6; mostly ultrasoft/PAW at 60/480 Ry), **M** (QE 7.5 from conda-forge, norm-conserving, 90 Ry) and **Y** (QE 7.6). They are **planning numbers and red-flag thresholds, not constants**. Re-measure on your own box with your own input (§7). The per-run table behind §5 is `assets/benchmarks/qe-jobs.csv`: 961 runs, with no paths, compositions or energies.

## 1. Units (read this first)

- **Busy wall-clock time:** hours during which at least one machine was computing a run that finished. It is the union over machines, not elapsed time: Projects A and M ran over 10.6 days, but finished runs were going for 89 h of them.
- **Busy machine-hours:** the same, per machine and summed. Two machines busy for one hour = 2 machine-hours.
- **Rank-hours:** wall time × MPI ranks × threads, summed over runs. This is what the jobs asked for.
- **Core-hours (core-time used):** one core busy for one hour = 1 core-hour. It is rank-hours, but never more than the machine's usable cores at any instant, so oversubscribed ranks add nothing. It is usage, not capacity: box D was busy 38.2 h, a capacity of 64 × 38.2 = 2,445 core-hours, of which 1,687 were used.
- **Money is per box-hour**, not per core-hour (box D: $0.537–0.56/h).
- Every total is a **floor**: runs that were killed print no wall time and are not counted.

## 2. The machines

| Box (project) | Provider | CPU | Usable cores | RAM / cgroup | /dev/shm, disk | Price | Verdict |
|---|---|---|---|---|---|---|---|
| Host A (A) | vast | 2× EPYC 7K62 (96 c / 192 thr) | **46.08** (cgroup cpu.max) | ~416 GB available | — | — | Usable only at ≤ 46 ranks. Early runs at 188 ranks were 4× oversubscribed (§4.6) |
| Host B (A) | vast | 2× EPYC 7C13 (128 c / 256 thr) | **70.2** (cpu.max) | ~390 GB available | — | — | Good once slots matched the quota |
| Host C (A) | vast | EPYC 7K62 (48 c) | 46 | 125 GB | 31 GB shm; /workspace not a volume | — | Good; slowed 2.5× after a host reboot (§4.8) |
| TR box (A, "Host D" in the Sep logs) | vast | Threadripper 2970WX (24 c / 48 thr) | 24 | — | — | — | Fine for 20-atom work; SMT left unused |
| box R (A, recovery) | vast | 2× EPYC 7K62 | 46.08 | 242 GiB cap | 62 GB shm, 31 GB overlay free | — | Used for the pool-layout trial (§4.1) |
| box 1 (A) | vast | EPYC 7J13 | 64 | 251 GB | 125 GB shm, 32 GB disk | — | About 1.6× slower per core than Host B on the same input |
| box 2 (A) | vast | EPYC 7K62 (48 c), 2× RTX 3090 | 46.08 | 157 GB | 39 GB shm | — | Within 5% of box 1 per core; 6-hour rental |
| box A (A) | vast | share of a multi-GPU host | ~8 Zen 4 core-equivalents (cpu.shares) | — | — | — | **Rejected**: shared, and one socket 3× slower |
| box B (A) | vast | EPYC 9684X, sold as "whole machine" | — | — | — | — | **Rejected**: overloaded, 1-core dgemm ~5.6 GFLOPS, 5-atom test 7× slower than box 1 |
| box D (A, then M) | vast | EPYC 7Y83 (64 c / 128 thr), whole machine | 64 (quota 122.88, not limiting) | 125 GB (~120 GiB cgroup) | 60 GB disk | $0.537–0.56/h | Best box; one instance served both projects |
| box E (M) | vast | 2× EPYC 7K62 | 46 | 259 GB | 32 GB disk | — | Good; digit-identical energies to box D |
| GCP box (M) | Google Cloud | EPYC 7B13, 1 thread/core | 8 | 31 GB | 70 GB free | — | Fastest per core measured (§3.3) |
| local PC (M) | Windows + WSL | — | 4 ranks | — | — | — | First pass of one compound only |
| first box (Y) | vast | EPYC 7B13 | 64 | 503 GB | 125 GB shm | — | Run shapes certified here (§4.4) |
| box 1 (Y) | vast | 2× EPYC 7K62 | 46 (quota) | 242 GiB | 62 GB shm | — | Sanity SCF took about 14% less time than on the 7B13 box |
| box 2 (Y) | vast | 2× EPYC 7763 | 61.4 (quota) | 484 GiB | 125 GB shm | — | Busy host (load 77–103): same input 26% slower than Y box 1 |
| box 4 (Y) | vast | 2× EPYC 7C13, 2× A4000 | 70.2 | 503 GB host, **277 GB cgroup** | — | — | OOM at 1 rank per pool on large cells (§4.3) |
| box 5 (Y) | vast | EPYC 7532 (32 c), 2× RTX 5060 Ti | 61 (quota, but 32 physical) | 130 GB | — | $0.372/h | Single socket: a NUMA-half allocator could not place a 16-rank job |

Read three things from this table:
- **`nproc` and the dashboard lie; `cpu.max` and `lscpu` don't.** Host A showed 192 CPUs and allowed 46.
- **Two of five Project A rentals in one night were unusable.** Benchmark before moving work (§7).
- **GPUs were never used for QE.** They were dead weight on every box.

## 3. Same-input speed comparisons (the fair ones)

### 3.1 Project A validation inputs (s per SCF iteration, 8 ranks unless noted)

| Input | box D (7Y83) | box A solo | box 1 (7J13) | box B (9684X, overloaded) |
|---|---|---|---|---|
| 5-atom static, 8 ranks | **1.91** | 2.3 | 5.5 | **39.5** |
| same, 4 copies at once on disjoint cores | 2.55 each | — | — | — |
| 20-atom cell, 24 ranks | **16.6** | — | 30.3 | — |

Per core (core-seconds per k-point per SCF iteration, identical inputs):
- **5-atom input:** box 2 0.61, box 1 0.59.
- **20-atom input:** box 2 18.2, box 1 15.2 when half loaded and 17.8 when fully loaded.
- So box 1 and box 2 were within ~5% per core under full load. Box D was ~1.8× box 1 on the 20-atom input and 2.9× on the 5-atom input.

### 3.2 Project M environment check (8-atom norm-conserving SCF, 11 iterations, same energy to every digit)

| Ranks | box D (7Y83) | box E (7K62, quota 46) |
|---|---|---|
| 8 | 16.6 s | 38.8 s |
| 16 | 10.75 s | 28.9 s |
| 32 | 7.82 s | 17.7 s |
| 8, a second 8-atom input | 105.7 s | 99.9 s |

A small cell gains only about 2.1× from 8 to 32 ranks. On the first input box E was 2.3–2.7× slower than box D; on the second it was 6% faster. Per-box speed depends on the load at that moment (§3.3), so measure it and record it.

On the GCP 7B13 box (8 ranks, 8-atom SCF), `-nk 2 / 4 / 8` gave 11.0 / 14.2 / 13.1 s with identical energies, so for a small cell on 8 ranks fewer pools was fastest.

### 3.3 One core, loaded box versus quiet box (Yambo RPA, same run)

The GCP 7B13 took 914 s on one core. Box D took 3,271 s for the same 1-core run while its other cores were busy: **3.6× slower**. A box's per-core speed under full load can be far below its idle speed. Benchmark under the load you will actually run.

### 3.4 Project Y: same input on two boxes

The ~23-atom sanity SCF took 13 m 31 s on Y's first box (EPYC 7B13), 11 m 34 s on Y box 1 (2× EPYC 7K62, quota 46) and 14 m 35 s on Y box 2 (2× EPYC 7763, busy host). Box 2 was 26% slower than box 1 and 8% slower than the 7B13 box.

## 4. Parallel-layout experiments

### 4.1 k-point pools for 40-atom cells (A): the biggest single gain

**box R, 40-atom spin-polarised SCF, 36 k points, two 20-minute windows on the same input:**

| Layout | SCF iterations in 20 min | Wall at iteration 25 | Mean CPUs used | Throttled periods | Peak memory above baseline |
|---|---|---|---|---|---|
| 46 ranks, 2 pools (23 per pool) | 25 | 1176.8 s | 45.9 | 5,933 of 12,021 | 8.5 GiB |
| 36 ranks, 6 pools (6 per pool) | 28 | **1081.6 s** | 36.0 | 0 of 12,032 | 11.0 GiB |

The 6-per-pool layout was 8% faster with 22% fewer ranks, and stopped hitting the quota. Part of the 8% is less work: the 36/6 run also did ~5% fewer Davidson iterations. The 23-ranks-per-pool FFT split was poor too (23 divides neither 100 nor 72 planes).

**box 1, the same 40-atom family at 36 ranks:**
- npool 18 (2 ranks per pool): 259–336 s per iteration.
- After relaunching at npool 6: 118 s at equal Davidson work, a **2.2× speed-up**.
- Rule adopted: at least 6 ranks per pool for 40-atom cells. Box D 40-atom jobs at 6–7 ranks per pool then ran at a median 94 s per iteration.

**Host C and the TR box (tilted 40-atom cell):**
- Host C: 46 ranks, nk 23, ~110 s per iteration.
- TR box: 24 ranks, nk 12, ~130 s per iteration.
- One rank per pool was estimated to gain only ~10%, and not tried mid-SCF.

### 4.2 Scaling a 20-atom relaxation (A)

np 10 / nk 10 took ~950 s per BFGS step, and np 32 / nk 16 took ~350 s: 2.7× for 3.2× the ranks. A vc-relax is a serial chain of BFGS steps; only per-step parallelism helps, and it is capped by the k-point count.

### 4.3 Pools versus memory (Y, A)

- **Y:** displacement SCFs at np 8 / nk 8 used 9–11 GB per rank (70–91 GB per job). All of them were OOM-killed (13 kills) under a 277 GB cgroup cap on a 503 GB host. nk 2 stopped the OOM, but at 8 ranks the 72-atom jobs then took ~23 min per SCF step and were dropped. Rule: when available RAM < 20%, halve `-nk` on the next launch.
- **A:** the 40-atom SCF at 46 ranks / 2 pools (23 per pool): QE's estimate was > 27.3 GB total. Measured peak memory above baseline was 8.5 GiB for 46/2 and 11.0 GiB for 36/6.

### 4.4 Run-shape certification (Y's first box, EPYC 7B13, ~23-atom cell)

| Shape | Wall for the sanity SCF |
|---|---|
| 8 ranks, no pools | 811 s |
| **8 ranks, -nk 4** | **716 s** (default for waves of jobs) |
| 8 ranks, -nk 8 | 829 s |
| 31 ranks, -nk 31 (101 k points) | ~6 min |

For many independent jobs, use one 8-core block per job (one L3 group). For the one job everything waits on, use a large slot, but a ~23-atom cell gets about 4–6× from 64 cores, not 8×. A running mpirun cannot grow, so give the big slot at launch.

### 4.5 Hyperthreads (A box 1)

An 18-rank job was placed on the SMT siblings of a running 18-rank job for 6.5 minutes:
- The running job slowed from 70–90 s per iteration to **445 s**.
- The intruder ran at 153 s per iteration instead of the ~40 s expected on physical cores.

One rank per physical core. The dashboard's "50% CPU" meant 64 of 128 logical CPUs, i.e. fully used.

### 4.6 Oversubscription (A, first night)

Host A ran the frozen-phonon SCFs at **188 ranks on a 46.08-CPU quota**. Host B ran 8 slots × 16 = 128 ranks on 70.2.

Found by reading `cpu.max`. The fix:
- Jobs were killed and requeued at quota-sized slots: A 5 × 8, B 8 × 8, plus one 4-rank slot each.
- Measured afterwards: A 40–44 of 46 CPUs and B 64–68 of 70 busy, with 0 throttled periods.

### 4.7 Cell size versus slot size (A)

A 30-atom cell with 51 k points and 126 bands on an 8-rank slot ran ~300 s per iteration, more than 10 h per relaxation. It was killed. Rule: no 30-atom cells on 8-rank slots; size the slot from a measured s/iteration.

### 4.8 Contention you cannot fix (A Host C)

After a host reboot, the same tilted 40-atom relaxation ran ~245–354 s per iteration instead of ~120 s. The quota was unchanged, throttling was small, the clock was 3.27 GHz and the load equalled our 46 ranks. This was shared-host contention, and it stretched the first SCF from ~2 h to 5–6 h. Benchmark again after any host event.

### 4.9 Yambo layouts (M box D, RPA, 128 bands, 1201 points)

| Ranks × threads | Wall | Speed-up vs 1 core | Efficiency |
|---|---|---|---|
| 1 × 1 | 3271 s | 1.0 | — |
| 16 × 1 (X over k c v) | **325 s** | 10.1 | 63% |
| 16 × 1 (X over g k) | 331 s | 9.9 | 62% |
| 4 × 4 | 548 s | 6.0 | 37% |
| 8 × 2 | 629 s | 5.2 | 33% |

Decision: pure MPI, one thread per rank. Split over g only when the X matrix needs splitting for memory: 8 Ry is ~1.1 GB per rank unsplit, 16 Ry ~8.8 GB per rank.

### 4.10 Reproducibility across layouts and hosts (M, A)

- **Energies were identical to every printed digit** across 8, 16 and 32 ranks, across nk 2, 4 and 8, and across hosts (7K62 against 7Y83, and every Project A box against the paper inputs).
- Forces moved by ≤ 1.6e-7 Ry/bohr and stress by ≤ 0.01 kbar. Record that as a measurement, not a gate failure.
- A hybrid MPI+OpenMP build started 8 threads per rank until `OMP_NUM_THREADS=1` was set (GCP banner: "Threads/MPI process: 8").

### 4.11 Packing a 64-core box (M box D)

- **Planning:** a reviewed capacity plan kept reservations ≤ 64 cores, counting QUEUED as well as RUNNING jobs.
- **Measured:** an independent 5-second sample saw **62.01 cores busy** with 62 reserved.
- **Fixed job sizes leave gaps.** Do not exceed the box to fill the last few cores.
- **Disk was the limit, not CPU.** ph.x with electric fields wrote ~1 GB each of dwf, ebar, mixd and recovery files per compound, and filled an 8.5 GiB overlay (`common-mistakes.md`).

## 5. What the campaigns ran (Projects A and M, from `qe_bench.py`)

There were 1,020 output files. 59 were copies of the same run (mirrors, snapshots, post-processing folders; 14 of them under another box's folder), leaving **961 runs**. Of these, 67 have no wall time (killed or still running at the last sync).

| Box | Runs | Busy machine-hours | Rank-hours | Usable cores | Peak ranks | Core-hours |
|---|---|---|---|---|---|---|
| box D (A then M) | 181 | 38.2 | 1,687 | 64 | 64 | 1,687 |
| box E (M) | 107 | 20.4 | 823 | 46 | 46 | 823 |
| Host B (A) | 173 | 19.0 | 737 | 70 | 68 | 737 |
| Host A (A) | 117 | 16.4 | 410 | 46 | 48 | 409 |
| Hosts A+B, first night (A, not separable) | 177 | 5.9 | 707 | 116 | **444** | 376 |
| Host C (A) | 68 | 11.1 | 322 | 46 | 46 | 322 |
| TR box (A) | 21 | 7.4 | 166 | 24 | 24 | 166 |
| GCP (M) | 49 | 15.9 | 123 | 8 | 8 | 123 |
| box 2, box 1, box R (A) | 26 | 8.1 | 154 | 46–64 | ≤ 46 | 154 |
| local PC (M) | 40 | 11.4 | 91 | 4 | 8 | 46 |
| box A/B tests (A) | 2 | 0 | 0 | — | 0 | 0 |
| **All** | 961 | **154 machine-hours in 89 h of busy wall-clock** | 5,221 | | | **≈ 4,840** |

How to read it:
- 89 h of busy wall-clock time (3.7 days, within a 10.6-day span) with 1.7 machines busy on average gives about 4,800 core-hours. One machine ran alone for 45 h of the 89, two for 27 h, three for 13 h and four for 4 h. Box D alone was busy 38 h with ~44 cores working on average.
- The rented machines alone account for 83 h of busy time, 142 machine-hours and ~4,800 core-hours; the local PC adds 46.
- The rental itself was longer (setup, validation, idle gaps, the 67 runs with no wall time (killed, or still running at the last sync), Yambo): about 5–7 days in total.
- Peak > cores flags the oversubscribed first night (444 ranks on 116 CPUs) and the 8-rank runs on the 4-core PC.

Typical durations (finished runs; median and 90th percentile wall time, lower-index method):

| Project | Kind | Atoms | Runs | Ranks (median) | k points (median) | Median | 90th pct |
|---|---|---|---|---|---|---|---|
| A | scf | ≤ 10 | 156 | 18 | 64 | 52 s | 5 min |
| A | scf | 11–20 | 189 | 8 | 45 | 18 min | 50 min |
| A | scf | 31–45 | 11 | 188 (oversubscribed) | 10 | 13 min | 1.5 h |
| A | relax | 11–20 | 40 | 8 | 20 | 40 min | 1.0 h |
| A | vc-relax | ≤ 10 | 30 | 8 | 40 | 4 min | 1.4 h |
| A | vc-relax | 11–20 | 30 | 8 | 26 | 2.4 h | 4.3 h |
| A | ph.x | ≤ 10 | 8 | 32 | 80 | 11 min | 53 min |
| M | scf | ≤ 10 | 107 | 8 | 14 | 46 s | 4 min |
| M | vc-relax | ≤ 10 | 64 | 7 | 14 | 7 min | 18 min |
| M | relax (elastic strains) | ≤ 10 | 128 | 9 | 36 | 34 min | 1.6 h |
| M | nscf / bands | ≤ 10 | 31 | 8 | 260 | 9 min | 16 min |
| M | ph.x, one q point per job | ≤ 10 | 30 | 4 | 128 | **5.3 h** | **8.8 h** |
| A | 40-atom tilted vc-relax (box D, 36 ranks, 6 pools, 63 k) | 40 | 1 | 36 | 63 | 13.4 h | — |

The 40-atom tilted relaxations and the per-q phonons were the long poles. Plan box rental around them, not around the median job.

## 6. Rules that held (each traceable to a row above)

1. **Usable cores = `cpu.max` quota / period**, capped by physical cores. Never `nproc`, never the dashboard.
2. **One rank per physical core.** SMT siblings cost the running job up to 5× (§4.5).
3. **Pools:**
   - small cells: pools = ranks is fine;
   - 40-atom cells: about 6 ranks per pool, which beat both 2 per pool (2.2×, box 1) and 23 per pool (8%, box R);
   - large cells: `nk ≤ ranks/4` for memory;
   - never more pools than irreducible k points;
   - prefer ranks per pool that divide the FFT planes.
4. **Small cells stop scaling early:** ~2× from 8 to 32 ranks for an 8-atom cell, and 4–6× from 64 cores for ~23 atoms. Run many small jobs in 8-core blocks instead.
5. **Benchmark exclusivity before production:** the same small input solo and 4× concurrent, plus a 1-core dgemm (§7). Reject a box whose numbers are several times worse than the last good one.
6. **Benchmark under load, and again after any host event** (§3.3, §4.8).
7. **Pure MPI with `OMP_NUM_THREADS=1`.** Hybrid layouts lost in every test (QE and Yambo).
8. **Check the layout cannot change the answer:** energy identical to every printed digit across layouts and hosts.
9. **Disk and memory limit packing before CPU does** (ph.x scratch, `/dev/shm`, cgroup memory).

## 7. Benchmark your own box and campaign

1. **On a new box:** `bash scripts/box_check.sh --dgemm` (limits, siblings, quota, 1-core dgemm). Then run one small finished production input solo and as 4 concurrent copies on disjoint cores, and record s/iteration in `BOXES.md`.
2. **Validation:** `bash scripts/box_check.sh --validate PW_X INPUT EXPECTED_RY NP [NK]` must reproduce the energy to every printed digit.
3. **Layout:** before a long job, run 2–3 shapes of the real input for a few SCF iterations each. Compare s/iteration at equal Davidson work, and log the chosen shape as a decision.
4. **Campaign accounting:** map each mirror folder to its box and give each box its usable cores. Then run:
   ```
   python3 scripts/qe_bench.py --map hosts.json --exclude '/ref/' --csv qe-jobs.csv <project>
   ```
   where `hosts.json` has entries like `[["boxd-nc/", "box D 7Y83", 64], ["boxe-nc/", "box E 7K62", 46]]` (see `assets/examples/bench-hosts.json`). The tool:
   - drops copies;
   - flags runs found under two boxes;
   - reports busy box-hours, rank-hours and capped core-hours side by side;
   - flags oversubscription;
   - prints matched-shape per-core comparisons.
