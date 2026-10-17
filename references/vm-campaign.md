# Running a campaign on rented VMs

Contents: 1 Choosing and renting · 2 Benchmarking a new box · 3 Building and validating QE · 4 MPI, binding, pools, threads · 5 Memory, disk and scratch · 6 Scheduler design · 7 Monitoring (status, watcher, hourly check) · 8 Sync · 9 Remote process safety · 10 Migrating jobs between boxes · 11 Releasing a box · 12 Windows hosts

All of this comes from Project A's C051–C067 campaigns (vast boxes 1, 2, A, B, D), Project M's box D, box E and GCP box, and Project Y's boxes (a first 7B13 box, then boxes 1, 2, 4 and 5; see `case-studies.md`; measured numbers in `benchmarks.md`).

---

## 1. Choosing and renting

- **The user decides money.** Search and compare freely, but rent, extend or destroy only after the user says so. "Do what's best" in the middle of a campaign authorised replacing a bad box; it does not authorise new spend categories.
- **Physical cores are what matter for QE.** vast's `cpu_cores_effective` and the dashboard "CPU %" count hyperthreads. A dashboard reading of 50% CPU with one rank per physical core is 100% use.
- **The GPUs are dead weight for CPU QE.** Workstation and consumer cards run FP64 at about 1/64 of their headline speed. A GPU QE build means installing NVHPC on a 32 GB disk and validating a second build mid-campaign. vast does not rent CPUs without a GPU, so pick the cheapest card attached to the most cores.
- **Prefer whole machines** (`gpu_frac 1.0`). Shared hosts throttle through `cpu.shares` or are oversubscribed.
- Weigh newer cores against more cores. Zen 4 with AVX-512 and DDR5 was about 2.4× faster per core than Zen 3 on one socket of box A, but that box was shared. Check RAM per rank as well: box 1 used about 35 GB in total for three jobs at 64 ranks (36 + 10 + 18), including a 40-atom spin-polarised cell.
- **vast API, as of Oct 2026.** Offer search is `POST https://console.vast.ai/api/v0/bundles/` with a JSON query body. Instances are `GET https://console.vast.ai/api/v1/instances/`; v0 returns 410. Auth header `Authorization: Bearer $VAST_KEY`. The `vastai` CLI needs a newer Python than macOS system 3.9, so use curl or requests. Field gotchas: `cpu_cores_effective` counts threads, `duration` is seconds until the offer ends, and filtering by offer ID on the bundles endpoint returns nothing (search, then match). Offers vanish, so rent soon after deciding.
- Keep the provider API key in an env file outside every repository (its location belongs in `LOCAL.md`, see SKILL.md). Read it into an environment variable for the one process that needs it; never echo it, never copy it, never write it to RUNLOG, memory or the box, and never ask the user to paste a key into chat.
- Record each box in the plan or handoff: instance ID, ssh host:port, CPU model, physical cores, cgroup quota, RAM, `/dev/shm` size, disk, price, rental end. Give boxes stable names (box 1, box 2, box D) and never reuse a name.

## 2. Benchmarking a new box (before any production)

Measured numbers for every box we rented (same-input speeds, pool layouts, SMT, oversubscription, Yambo layouts) are in `benchmarks.md`. Two of five Project A rentals were unusable. Box A was a share of a multi-GPU host, about 8 Zen 4 core-equivalents through `cpu.shares`, and one socket was 3× slower. Box B was overloaded: 1-core dgemm at about 5.6 GFLOPS, and the 8-rank 5-atom test ran about 7× slower than on box 1 (39.5 vs 5.5 s/iteration). The test that exposed them takes under 10 minutes:

1. `bash box_check.sh --dgemm` (from the skill's scripts) prints all of the following at once: `lscpu`, `nproc`, physical cores, `cpu.max`/`memory.max`, `free -g`, `df -h / /dev/shm`, the sibling numbering (`thread_siblings_list`, e.g. 0,64), the GPUs and a 1-core dgemm.
2. Run a small known input (Project A used a 5-atom static at 8 ranks) **solo**, then **four copies concurrently** on disjoint cores. The per-iteration time must stay roughly flat, otherwise cores are shared.
3. Run a single-core dgemm (numpy with OpenBLAS limited to 1 thread). Compare against an earlier box.
4. On a dual-socket box, run the test on each socket: one socket can be contended while the other is free.
5. Express speed as **core-seconds per k-point per SCF iteration** on an identical input, so different boxes compare fairly. Box 1 and box 2 were within 5% per core; box D was about 1.8× box 1 on a 20-atom input and 2.9× on a 5-atom one.
6. Hyperthreads: measure, don't assume. On box 1, an extra job on the sibling threads slowed the real job from about 80 s to 445 s per iteration and itself ran at quarter speed. **One rank per physical core.** Adopt SMT only with a measured gain of at least 10%.

## 3. Building and validating QE

- **Match the earlier runs exactly.** Project A rebuilt QE 7.3.1 from the GitHub tag (tarball SHA-256 recorded) with the paper `make.inc` flags `DFLAGS = -D__FFTW3 -D__MPI -D__SCALAPACK`, gfortran -O3, OpenBLAS, ScaLAPACK-openmpi, FFTW3 and Open MPI 4.1.6. Project M used conda-forge `qe-7.5-h19104ac_2` and proved the environments package-identical with `micromamba list` diffs (`env-qe.diff`).
- A configure run that silently drops `__FFTW3` fails in FFTXlib. Check `make.inc` before building, and `ldd pw.x` afterwards (OpenBLAS, FFTW3, ScaLAPACK, MPI).
- Running `pw.x` with no input waits on stdin forever. Version checks use `pw.x -h </dev/null` or read the banner of a real run.
- QE does not create missing parent directories for `outdir` (`/dev/shm/qe/...`). Create them before the launch.
- zsh does not word-split `$var` in `for` loops the way bash does. Write box-side loops in bash scripts, not inline from a zsh shell.
- Verify the pseudopotentials on the box: compute SHA-256 and compare against the recorded set (`pseudopotentials.json` or the pseudo README). Mismatch is a hard stop.
- **Validation gate** (`box_check.sh --validate PW_X INPUT EXPECTED_RY NP [NK]`). Rerun one or two finished production inputs with only `pseudo_dir` and `outdir` changed. Prove that with `diff` after filtering those two lines. Require:
  - total energy equal to every printed digit (Project A: a 5-atom and a 20-atom paper input reproduced to all eight decimals on each box);
  - forces and stress equal within summation-order noise. A different rank layout moved forces by up to 1.6e-7 Ry/bohr and stress by 0.01 kbar, never the energy. Record that as a measurement in `layout.dat`, not as a gate failure.
- With a hybrid MPI+OpenMP build, QE starts N threads per rank unless `OMP_NUM_THREADS=1` is set. The banner shows "Threads/MPI process: 8".

## 4. MPI, binding, pools, threads

Environment for every launch:

```
export OMPI_ALLOW_RUN_AS_ROOT=1 OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export HWLOC_COMPONENTS=-gl,-opencl,-cuda,-nvml   # without it mpirun hangs silently on vast (hwloc gl probes X)
export PMIX_MCA_gds=hash                          # Open MPI 4 in some containers: OUT-OF-RESOURCE at MPI_Init
```

- Never use `--allow-run-as-root`; use the env vars. Never `killall sshd` on vast, because it kills the ssh gateway.
- **Bind explicitly.** Run `taskset -c <disjoint list> mpirun --bind-to none -np N`. Open MPI 5 ignored the MCA binding env var and pinned six jobs to cores 0–15. Default bindings of several mpiruns overlap.
- Redirect mpirun stdin from `/dev/null`, especially inside `while read` loops. Close lock fds for children (`9>&-`), otherwise ranks inherit the scheduler's flock.
- **k-point pools** (`-nk`). The layout for a new system comes from a measured s/iteration on that system; the examples below are starting points, not rules. The pool count must divide the rank count and must not exceed the irreducible k count QE will find. Estimate that count with spglib at a generous tolerance, so you never ask for more pools than QE creates.
  - Small cells (5–20 atoms): pools = ranks is fine.
  - Measured example (A, 40-atom cells): at least 6 ranks per pool worked; 2 ranks per pool ran 259–336 s per iteration against 118 s at 6 per pool.
  - Measured example (Y, ≳70 atoms): `nk ≤ ranks/4` was needed. With `-nk = ranks`, every rank holds a full Davidson workspace, 9–11 GB per rank; 72-atom phonon SCFs were OOM-killed under a 277 GB cgroup cap on a 503 GB host.
- Check what QE actually found before choosing pools: "number of k points=" and the symmetry line. "No symmetry found" on an ML-rattled seed multiplies the k count. Symmetrise the seed first (spglib `standardize`/`refine` at 0.01 Å), when the structure really has that symmetry.
- `dos.x` rejects k-point pools, so run it on one rank. `projwfc.x` and `bands.x` can use the pw.x layout.

## 5. Memory, disk and scratch

- Put `outdir` on `/dev/shm` when RAM allows. It is fast, but it counts against the cgroup memory cap.
- **Clean scratch when a job ends.** A finished 24-atom, 101-k job leaves 2.5–3 GB of `wfc*.dat`. After about 25 jobs, `/dev/shm` filled up and later jobs died in `write_rhog` after their SCF converged (the `!` energies were still valid). The scheduler deletes the scratch of finished relaxations and failures, and keeps static scratch only when bands or PDOS will reuse it. Use `disk_io='nowf'` (or `'none'`) for single points nobody restarts from.
- **Measure peak scratch before running jobs concurrently**, especially ph.x with electric fields. Project M step 86 scaled the old SCF footprint (about 150–185 MiB) and omitted the dwf, ebar, mixd and recovery files: about 1 GB each per compound. An 8.5 GiB overlay hit 8 MiB free, one compound crashed with `davcio` error 22, and the other had to be frozen with SIGSTOP. `SIGSTOP` is not a checkpoint.
- Hard stops in the scheduler: free disk < 5 GB or MemAvailable < 12 GB means no new launches (write `STOP`). Free disk < 5 GB on the box is a hard stop for the operator too.
- Watch the cgroup OOM counter after big launches: `cat /sys/fs/cgroup/memory.events` (oom_kill).
- Before queuing any cell of ≳50 atoms, estimate per-rank memory from the first job's VmRSS.

## 6. Scheduler design

Each project rewrote its scheduler (Project A `qsched.py`, Project M `qrun.sh` plus `launch.sh`, Project Y `queue_runner.py`/`orchestrator.py`). `scripts/qsched.py` is the generalised Project A C067 version that survived a hostile Codex launch review. Whatever you use, it must have these properties. Each line is a bug that a review or an incident found.

- **Single instance**: an `flock` on a lock file, with the fd closed for children.
- **Liveness by `/proc/<pid>/cwd`** (any non-zombie process whose cwd is the job directory), never `pgrep -f`. A job with live processes is **adopted, never relaunched**. That makes restarts and PID reuse safe.
- **State written atomically** (tmp file plus `os.replace`), and recorded *before* `Popen`, so a crash in between is covered by adoption.
- **Iterate over a snapshot** (`list(st["jobs"].items())`). Codex found a dict-mutation crash at the first follow-up.
- **Strict outcome classification.** For SCF: `JOB DONE` and "convergence has been achieved", and no "convergence NOT achieved". For relax/vc-relax: also "bfgs converged" and "End final coordinates". "The maximum number of steps has been reached" is a failure. **Never auto-retry a failure.**
- **Follow-up chains built idempotently on every loop** (coarse relax `_vrC` → fine relax `_vrF` → static `p0_*_scF` → one-parameter tests). Every child gets its geometry from the parent's final block, a k mesh recomputed from the spacing rule, a **structure gate** and a `FORMULA-CHECK.md`. A failed gate marks the child BLOCKED. Assert that each regex substitution matched exactly once (`subn == 1`).
- **One-parameter tests** copy the parent input and change exactly one thing (ecut pair, k spacing, smearing width). Prove that offline with a diff.
- **Resources**: disjoint taskset core lists, `ranks = min(ranks_max, free)` if ≥ `ranks_min`, pools as in §4, reservations counted for QUEUED as well as RUNNING (Project M `CORES` files), and optional `ready.sh` dependency checks. Backfill can starve a large head job, so reorder the queue if small jobs keep arriving.
- **Hard stops and pause**: a `STOP` file pauses new launches while running jobs continue.
- **Logs**: one line per START/END/ADOPT/QUEUED/FOLLOWUP-ERROR/HARD-STOP, UTC stamps, and exceptions caught and logged (`LOOP-ERROR`) so the loop survives.
- Ignore SIGHUP, start children with `start_new_session=True` and stdin from `/dev/null`, and run detached (`setsid nohup`).
- **Never change a running step's logic underneath it.** Deploy reviewed files with `deploy.sh` (it verifies SHA-256 on the box against local and writes a manifest, like Project M `ops/deploy-*.json`), then restart the scheduler through an uploaded script. Syntax-check first (`python -m py_compile qsched.py`, `bash -n`). A syntax slip in an inline edit stopped the Project A scheduler once.
- A naming rule must not match by accident. "40-atom pool rule matching `_n8_`" relaunched a 20-atom job at npool 1. Store `nat` in the job record instead of parsing names.
- **Offline test before deployment.** Project A rebuilt the paper static from its relaxation with zero diff, checked that each test variant changed exactly one parameter, checked that gates passed, and checked that a second pass was idempotent.

## 7. Monitoring

### Status script (box side)

`scripts/qe_status.py` prints one line per job plus box health: state, result, ranks, elapsed hours, SCF count, last energy, ΔE per formula unit against the reference, total force, pressure, |M|, SCF iteration, accuracy, and output age in minutes. Alerts:
- `ALERT-STALE`: a running job with no pw.out write for more than 30 min;
- `ALERT-FAILED` or `ALERT-BLOCKED`, excluding deliberate `STOPPED(...)` jobs (otherwise every user-ordered stop becomes an alert);
- `ALERT-SCHEDULER-DEAD`, checked through `/proc/*/cmdline` with argv[1] ending in the scheduler name;
- `ALERT-SCHEDLOG`: LOOP-ERROR, HARD-STOP or FOLLOWUP-ERROR in the last hour;
- `ALERT-MEM`: MemAvailable < 15 GiB;
- `ALERT-NOTCONV`, `ALERT-EXITSTOP`, `ALERT-EIGWARN` from the raw output.

### Watcher (laptop side)

`scripts/watch.sh`, one per box, kept awake with `caffeinate -i` on macOS (Linux: `systemd-inhibit`, or plain `nohup` on a machine that does not sleep). Every 10 minutes it:
1. rsyncs the box queue into its **own mirror folder**, excluding scripts, `.lock` and `state.json.tmp`;
2. runs the status script over ssh (BatchMode, ConnectTimeout 30, ServerAliveInterval 30, `StrictHostKeyChecking=accept-new`);
3. appends any `ALERT` lines to `ALERTS.txt`, tagged `[boxN]`, and as a RUNLOG line ("no action taken");
4. on every sixth cycle writes the full status block to RUNLOG and `STATUS-latest.txt`;
5. on ssh failure counts consecutive failures and logs the first and then every sixth;
6. writes a pid file and refuses to start if another instance lives. Project A once had six concurrent watchers, because each Monitor re-arm on Windows left an orphan bash loop. They caused 6× ssh polling, load spikes and duplicate follow-up jobs.
7. stops on `WATCH-STOP`. **Touch WATCH-STOP when the box is released.**

### Claude side

- An hourly session cron (Claude Code: CronCreate; other agents: their scheduler, or a system cron that starts a headless agent run) with a self-contained prompt (template below), and an alert watch on `tail -n 0 -F <ALERTS.txt>` (Claude Code: the `Monitor` tool, timeout 3600000). The Monitor expires and must be re-armed each hour; the hourly check does that. Both end when the session ends, so state this in the handoff.
- Long-running Windows alternative (Project M): a Task Scheduler job polls STATUS every minute and queues a prompt to the orchestrator thread only on a change, a first outage or recovery, or every 30 minutes. It needs the user signed in and the machine awake, and it is not a remote hard stop.

### Hourly check prompt template

Fill in the brackets. Keep the prompt self-contained: it runs in a fresh turn and must not depend on memory.

```
<CAMPAIGN> HOURLY CHECK (autonomous, keep it short). Wrappers: <vsD> = <box D user@host:port> (<queue dir>, <N> cores).
NEVER use pkill/pgrep -f patterns that can match your own ssh line; kill explicit PIDs only; restart schedulers only
via uploaded scripts and syntax-check them first.
1) <vsD> 'cd <queue dir> && <python> qe_status.py ... && tail -6 sched.log'.
2) Watchers alive: ps -axo pid,command | grep "[w]atch_<box>.sh"; if dead restart from its dir with
   nohup caffeinate -i ./watch_<box>.sh > watch.stdout 2>&1 & (macOS; on Linux drop caffeinate).
3) Re-arm Monitor if not running: tail -n 0 -F <ALERTS.txt>, timeout 3600000, description '<CAMPAIGN> box alerts'.
4) On ALERT / stuck SCF (>150 iterations or accuracy flat >1 h) / idle cores with PENDING jobs / MemAvailable <15 GiB:
   diagnose from raw pw.out/pw.err; only conservative numerical fixes that keep the cited physics (never functional,
   pseudos, cutoffs, smearing, spin); get an Opus critique saved in <critique dir> (plus Codex if
   installed) BEFORE relaunching anything; record it with logbook.py decide; keep the aborted output.
5) <Box-specific deadline actions, e.g. final rsync before rental end; requeue an unfinished job on box D from its last
   evaluated geometry with a gate.>
6) When <decisive job> completes, compute <quantity> vs <reference> in <unit>, apply the pre-registered rule in
   <START cite file> and record it.
7) Log ONE concise line with the real clock: python3 <skill-dir>/scripts/logbook.py log <project or
   queue folder> CHECK "<CAMPAIGN> claude check: <state in numbers>" (never type a time by hand).
Message the user only if a decision needs them.
```

## 8. Sync

- Pull every 10 minutes. The box disk is not persistent: anything not pulled is lost when the instance goes.
- **Mirror, don't merge.** Pull into `queue_<name>/` or `boxd-nc/`, never over files you edit locally. If edited files must live in the same tree, use `rsync -a --update` after a `-n -i` dry run proves no edited file would be touched. After editing a script that also lives on the box, push it at once and compare hashes.
- Exclude regenerable bulk (`tmp/`, `*.save`, `SAVE/`, `ndb.*`, files over 20 MB). Then **say so in the handoff**: the sync is not a backup of scratch or SAVE directories.
- Advance the "last pulled" stamp only after archive, extraction and acknowledgement all succeed. A failed or partial pull stays eligible for the next cycle (Project M `sync.sh`). Expect benign retries when files grow during a pull. Remote `tar` needs `--ignore-failed-read`, because pw.x deletes scratch between `find` and `tar`.
- Before relying on a mirror (release, migration, paper numbers), run a checksum dry-run (`rsync -a -c -n -i`) and require zero differences, apart from files still being written by live jobs, which you then re-sync.

## 9. Remote process safety

- **Pattern kills over ssh kill yourself.** `pkill -f qsched.py` inside `ssh host '...'` matches the remote `bash -c` whose command line contains "qsched.py". It killed the Project A scheduler, and in Project Y it killed the agent's own commands. Wait loops built on `pgrep -f "<pattern>"` never end and block other waiters; GPU0 sat idle for 80 min.
- Instead: put remote logic in uploaded script files (their cmdline is just `bash script.sh`). Identify processes by `/proc/<pid>/comm` (e.g. `pw.x`), cwd and start time. Wait for output markers (JOB DONE, a model file), not for processes. Run long waits detached.
- To stop one job: record its PID, comm, cwd and start time, then kill exactly those PIDs (mpirun plus its ranks), and verify nothing remains. A clean QE stop can be requested by creating `<prefix>.EXIT` in the run directory, but the job then prints JOB DONE without being converged; rename such outputs or mark them STOPPED.
- After stopping a local launcher, check with `ps` that no launcher process survived before running anything again. An orphaned start loop once launched a second runner onto occupied cores (16 ranks on 8 CPUs).
- Dry-runs of a state-changing script use a separate probe-only script. A "read-only prefix" built with `head -n -1`, whose truncation grep did not match, executed a whole launch script against a live host.

## 10. Migrating jobs between boxes

- A running QE job cannot move. It restarts from its **last evaluated geometry**: the cell and positions printed before the last `!` energy, or the "Begin final coordinates" block if BFGS finished. Fresh BFGS and fresh scratch; it costs the step in progress.
- Choose the break point on purpose. Moving Project A's 40-atom fine-grid relaxation from coarse-stage SCF #4 was reviewed and accepted, because the fine stage must converge to the full criterion anyway. Record the lineage honestly ("coarse pre-relaxation stopped before convergence; fine relaxation started from its last evaluated geometry") and never use the coarse energy as a result.
- On the new box: build, validate (§3), benchmark (§2), regenerate the inputs from the evaluated geometry through the structure gate, prove the moved inputs are byte-identical to the gated set, mark the old entries `MOVED` so nothing runs twice, and only then start.
- Get a second check on any migration that skips part of a protocol.

## 11. Releasing a box

1. Pause launches (`touch STOP`). Let jobs finish, or record why they are stopped (`STOPPED(<reason>)`, outputs kept).
2. Do a final rsync of every queue folder, plus scheduler logs, validation runs and box-only scripts.
3. Run a checksum dry-run and require zero differences.
4. Record unfinished jobs and their last evaluated geometries in RUNLOG, and queue them elsewhere if needed.
5. Touch `WATCH-STOP` for that box's watcher and check that it exited.
6. Tell the user it is safe to destroy, or destroy it through the API if they asked. Then update the handoff and commit.

## 12. Windows hosts

- QE in WSL with micromamba: a non-interactive `wsl bash -lc` does not activate the env. Launch every job through a `_launch.sh` that sets `MAMBA_ROOT_PREFIX`, loads the hook, activates `qe`, `cd`s and runs mpirun.
- The Monitor tool's expiry does not kill a bash loop on Windows, so re-arming leaves orphans. Use pid files.
- Copy `~/.ssh/<key>` to `C:\Users\<you>\.ssh\` by a secure route, never via git. PowerShell's OpenSSH works for status checks. rsync needs WSL.
- Line endings: strip `\r` from cards copied from Windows files (`tr -d '\r'`).
