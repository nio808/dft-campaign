#!/usr/bin/env python3
"""Core-packing QE scheduler for ONE rented box (Linux). Template generalised from Project A's C067 qsched.py, the version
rewritten after a hostile Codex launch review (VERDICT LAUNCH=NO: dict-mutation crash, liveness, gates) and proven on
four vast boxes; hardened again after an Opus review of this template. Project-agnostic: every physics value (k spacings,
test parameters) and every machine value (pw.x path, cores, scratch policy) comes from qsched.json in the queue
directory, cited in the folder CITES.md. OFFLINE-TEST against old outputs before deploying.

usage:
  qsched.py run                                   start the scheduler loop in this directory (detach it, see below)
  qsched.py offline-test PARENT_DIR CHILD --calc scf --spacing 0.2 [--formula FORMULA] [--override JSON]
                                                  rebuild a follow-up (or, with --override, a one-parameter test
                                                  variant) and print it with its gate report; no QE, no /proc
  (no arguments or --help prints this text and exits; it never starts the loop)
Detached start on the box:  setsid nohup <python> qsched.py run >> sched.stdout 2>&1 < /dev/null &

Design (each line answers a real bug or review finding):
- One MPI rank per physical core. Each mpirun is confined by taskset to a DISJOINT cpu list with --bind-to none.
- Liveness = a non-zombie process whose /proc/<pid>/cwd is the job dir (realpath) AND whose comm is an MPI/QE
  process (mpirun, prterun, orted, pw.x, ...). Never pgrep -f. An operator shell or tail -f in a job dir is ignored.
  A PENDING job with live QE processes is ADOPTED, never relaunched (restart/pid-reuse safe). Single-instance flock.
- Jobs start in priority order when their parent is DONE: ranks = min(ranks_max, free) if >= ranks_min;
  npool = largest divisor of ranks <= irreducible k count with >= min_per_pool ranks per pool (6 for >= 40 atoms).
- Follow-ups (chains, one-parameter tests) are built idempotently every loop from the parent's final coordinates,
  with a k mesh recomputed from the spacing rule; each passes structure_gate.analyse() and writes FORMULA-CHECK.md;
  a failed gate BLOCKS the child; a build that fails 3 times BLOCKS it too (visible, never silent). Child names come
  from suffix replacement and must be unique: a name collision is logged, never overwritten.
- OK = JOB DONE + (vc-relax/relax) 'bfgs converged' + final coordinates, or (scf) 'convergence has been achieved';
  'convergence NOT achieved', 'bfgs failed' and EXIT-file stops are failures. Failures are NEVER retried.
- Scratch deletion is an explicit, cited qsched.json choice (default: delete nothing).
- Hard stops: free disk (min over /, queue dir, scratch) < 5 GiB or MemAvailable < 12 GiB -> STOP file, no new
  launches. touch STOP to pause; running jobs continue.
- State is written atomically and BEFORE Popen; the loop iterates over snapshots; exceptions are logged, not fatal.

Naming convention (from Project A; any base name works): coarse relax <base>_vrC -> fine relax <base>_vrF -> static <base>_scF, where a leading
priority tag pN_ becomes p0_ on the static (p1_X_vrF -> p0_X_scF); tests on a static p0_X_scF are p3_X_scF_e80/_k15/
_d005 (without a p0_ prefix: <name>_e80 ...).

jobs.json (list; every key cited in the folder CITES.md):
  name         str   job directory name (contains pw.in)            calc       "vc-relax" | "relax" | "scf"
  ranks        int   maximum MPI ranks                               ranks_min  int, default max(4, ranks // 2)
  priority     int   lower starts first                              nat        int, atoms in the cell (REQUIRED)
  nirr_est     int   irreducible k-point estimate (pool upper bound) min_per_pool int, default 6 if nat >= 40 else 1
  formula      str   REQUIRED, e.g. "LaTaON2" (structure gate)       label      "cis" | "trans" | null
  gate         dict  extra structure_gate.analyse kwargs, e.g. {"shells": ["Ta:O,N:6:2.4"], "expect_shell": "O4N2",
                     "pair_angle": "N"}; REQUIRED (shells + pair_angle) when label is set
  tests        bool  this job is a decisive static: queue the matched one-parameter tests when it is DONE
  tests_on_child bool  queue the tests on the static at the end of this job's chain
"""
import argparse
import fcntl
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import traceback

HERE = os.path.realpath(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import structure_gate as sg  # noqa: E402  (ship structure_gate.py next to this file)

# ============================== PROJECT CONFIG (no physics defaults) =============================================
# Every physics value comes from qsched.json in the queue directory, written by the project and cited in the folder
# CITES.md. Nothing project-specific is hard-coded here. Example: assets/examples/qsched.json (Project A C067 values).
#   pw            path to pw.x on the box                                   (required)
#   ncpus         physical cores to use, 0..ncpus-1 (check thread_siblings) (required)
#   chain_spacing k spacing (1/Å, 2π included) for fine relax + static     (required if any chain is used)
#   tests         [{"tag": "e80", "spacing": 0.2, "override": {"ecut": [80, 640]}}, ...]   (required if any job tests)
#   scratch                     default "/dev/shm/qe"
#   delete_scratch_done_relax   default false   (set true only with a cited reason, e.g. a disk rule)
#   delete_scratch_done_static  default false
#   delete_scratch_failed       default false   (some projects forbid any scratch deletion)
#   min_free_disk_gib / min_mem_gib   operational hard stops, default 5 / 12
#   env                         extra environment variables for mpirun (merged over the container defaults below)
CFG = {}
CONTAINER_ENV = {"OMPI_ALLOW_RUN_AS_ROOT": "1", "OMPI_ALLOW_RUN_AS_ROOT_CONFIRM": "1", "OMP_NUM_THREADS": "1",
                 "OPENBLAS_NUM_THREADS": "1", "HWLOC_COMPONENTS": "-gl,-opencl,-cuda,-nvml"}
LOOP_SECONDS = 30
MPI_COMMS = {"mpirun", "mpiexec", "mpiexec.hydra", "orterun", "prterun", "prte", "orted", "prted",
             "hydra_pmi_proxy", "taskset", "pw.x"}


def load_config(path=None, need_run=True):
    global CFG
    path = path or os.path.join(HERE, "qsched.json")
    if not os.path.isfile(path):
        sys.exit(f"{path} missing: write the project config (see the docstring and assets/examples/qsched.json)")
    CFG = json.load(open(path))
    if need_run:
        for k in ("pw", "ncpus"):
            if k not in CFG:
                sys.exit(f"qsched.json: required key '{k}' missing")
    CFG.setdefault("scratch", "/dev/shm/qe")
    for k in ("delete_scratch_done_relax", "delete_scratch_done_static", "delete_scratch_failed"):
        CFG.setdefault(k, False)
    CFG.setdefault("min_free_disk_gib", 5)
    CFG.setdefault("min_mem_gib", 12)
    CFG.setdefault("tests", [])
    return CFG


def live_comms():
    return MPI_COMMS | ({os.path.basename(CFG["pw"])[:15]} if CFG.get("pw") else set())


def children(name, job):
    """Follow-ups of a DONE job: list of (child_name, calc, kspacing, overrides or None).
    overrides=None -> geometry from the parent's final coordinates (chain child); a dict -> the parent's input geometry
    with exactly one parameter changed: {"ecut": [wfc, rho]} | {"degauss": x} | {} (k spacing only)."""
    if name.endswith("_vrC") or name.endswith("_vrF"):
        if "chain_spacing" not in CFG:
            raise ValueError("qsched.json has no chain_spacing (cited fine-relax/static k spacing)")
    if name.endswith("_vrC"):                                   # coarse relax -> fine relax
        return [(name[:-4] + "_vrF", job.get("calc", "vc-relax"), CFG["chain_spacing"], None)]   # same calc as parent
    if name.endswith("_vrF"):                                   # fine relax -> static
        base = name[:-4]
        if re.match(r"^p\d_", base):
            base = "p0_" + base[3:]
        return [(base + "_scF", "scf", CFG["chain_spacing"], None)]
    if job.get("tests"):                                        # decisive static -> matched one-parameter tests
        if not CFG.get("tests"):
            raise ValueError("job requests tests but qsched.json defines none")
        stem = ("p3_" + name[3:]) if name.startswith("p0_") else name
        return [(f"{stem}_{t['tag']}", "scf", t["spacing"], t.get("override", {})) for t in CFG["tests"]]
    return []


def gate(cell, sym, frac, job):
    """Structure gate for every input the scheduler writes: formula (required) + shells/labels from job['gate']."""
    kw = dict(job.get("gate") or {})
    if job.get("label"):
        kw.setdefault("expect_label", job["label"])
    ok, rep, _ = sg.analyse(cell, sym, frac, formula=job.get("formula"), **kw)
    return ok, rep
# =================================================================================================================

STATE = os.path.join(HERE, "state.json")
_warned = set()


def log(msg):
    line = f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {msg}"
    print(line, flush=True)
    with open(os.path.join(HERE, "sched.log"), "a") as f:
        f.write(line + "\n")


def save_state(st):
    tmp = STATE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(st, f, indent=1)
    os.replace(tmp, STATE)


def job_procs(d):
    """Live MPI/QE processes whose cwd is job dir d (realpath), with their allowed cpus."""
    d = os.path.realpath(d)
    out = []
    for p in os.listdir("/proc"):
        if not p.isdigit():
            continue
        try:
            if os.path.realpath(os.readlink(f"/proc/{p}/cwd")) != d:
                continue
            if open(f"/proc/{p}/comm").read().strip() not in live_comms():
                continue
            stat = open(f"/proc/{p}/stat").read()
            if stat.rsplit(")", 1)[1].split()[0] == "Z":
                continue
            cpus = re.search(r"Cpus_allowed_list:\s*(\S+)", open(f"/proc/{p}/status").read()).group(1)
            out.append((int(p), cpus))
        except (FileNotFoundError, ProcessLookupError, PermissionError, AttributeError, IndexError, OSError):
            continue
    return out


def expand(cl):
    s = []
    for part in cl.split(","):
        a, _, b = part.partition("-")
        s += list(range(int(a), int(b or a) + 1))
    return s


def nirr(cell, sym, frac, mesh):
    try:
        import numpy as np
        import spglib
        els = [sg.element(s) for s in sym]
        num = [sorted(set(els)).index(e) + 1 for e in els]
        m, _ = spglib.get_ir_reciprocal_mesh(mesh, (cell, frac, num), is_shift=[0, 0, 0], symprec=1e-3)
        return len(np.unique(m))  # generous symmetry -> never more pools than QE's k count
    except Exception as e:
        if "nirr" not in _warned:
            log(f"NIRR-FALLBACK irreducible k count unavailable ({e!r}); pools limited to 1 for generated children")
            _warned.add("nirr")
        return 1


def sub1(pat, rep, txt, flags=0):
    new, n = re.subn(pat, rep, txt, flags=flags)
    assert n == 1, f"pattern {pat!r} matched {n} times"
    return new


CARDS = ("ATOMIC_SPECIES", "ATOMIC_POSITIONS", "K_POINTS", "CELL_PARAMETERS", "OCCUPATIONS", "CONSTRAINTS",
         "ATOMIC_FORCES", "HUBBARD", "ADDITIONAL_K_POINTS", "ATOMIC_VELOCITIES", "SOLVENTS")


def split_cards(txt):
    blocks, cur = [], [None, []]
    for l in txt.splitlines(keepends=True):
        w = l.strip().split()
        if w and w[0].upper() in CARDS:
            blocks.append(cur)
            cur = [w[0].upper(), [l]]
        else:
            cur[1].append(l)
    blocks.append(cur)
    return blocks


def replace_geometry(txt, cell, sym, frac, mesh):
    """Replace CELL_PARAMETERS, ATOMIC_POSITIONS (keeping each atom's if_pos flags) and K_POINTS; every other card and
    namelist stays byte-identical and in place."""
    blocks = split_cards(txt)
    names = [b[0] for b in blocks]
    for need in ("CELL_PARAMETERS", "ATOMIC_POSITIONS", "K_POINTS"):
        assert names.count(need) == 1, f"{need} card appears {names.count(need)} times"
    old_pos = [l.split() for l in blocks[names.index("ATOMIC_POSITIONS")][1][1:] if l.strip()][:len(sym)]
    assert [p[0] for p in old_pos] == list(sym), "species order changed between parent input and output"
    flags = [(" " + " ".join(p[4:])) if len(p) > 4 else "" for p in old_pos]
    new = {"CELL_PARAMETERS": "CELL_PARAMETERS angstrom\n" + "".join(
               "  " + " ".join(f"{x:.10f}" for x in v) + "\n" for v in cell),
           "ATOMIC_POSITIONS": "ATOMIC_POSITIONS crystal\n" + "".join(
               f"  {s:<3} " + " ".join(f"{x:.10f}" for x in p) + fl + "\n" for s, p, fl in zip(sym, frac, flags)),
           "K_POINTS": "K_POINTS automatic\n" + "  {} {} {}  0 0 0\n".format(*mesh)}
    out = []
    for name, lines in blocks:
        if name in new:
            out.append(new[name] + ("\n" if lines and lines[-1].strip() == "" else ""))
        else:
            out.append("".join(lines))
    return "".join(out)


def write_child(child, txt, cell, sym, frac, job, note):
    ok, rep = gate(cell, sym, frac, job)
    d = os.path.join(HERE, child)
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "FORMULA-CHECK.md"), "w").write(f"# {child}\n\n{note}\n\n```\n{rep}\n```\n")
    if not ok:
        raise ValueError("structure gate FAIL: " + rep.splitlines()[-1])
    open(os.path.join(d, "pw.in"), "w").write(txt)
    open(os.path.join(d, "PARENT"), "w").write(note + "\n")


def build_followup(parent_dir, child, calc, ksp):
    txt = open(os.path.join(parent_dir, "pw.in")).read()
    out = open(os.path.join(parent_dir, "pw.out"), errors="replace").read()
    cell, sym, frac = sg.read_output(out, "final", txt)
    mesh = sg.kmesh(cell, ksp)
    txt = sub1(r"calculation\s*=\s*'[^']*'", f"calculation = '{calc}'", txt)
    txt = sub1(r"outdir\s*=\s*'[^']*'", f"outdir      = '{CFG.get('scratch', '/dev/shm/qe')}/{child}'", txt)
    new = replace_geometry(txt, cell, sym, frac, mesh)
    if calc == "scf":
        new = re.sub(r"&CELL\b.*?^\s*/\s*\n", "", new, flags=re.S | re.I | re.M)
        new = re.sub(r"&IONS\b.*?^\s*/\s*\n", "", new, flags=re.S | re.I | re.M)
        for key in ("tprnfor", "tstress"):   # the force/stress gates need both in every static
            if not re.search(rf"{key}\s*=\s*\.true\.", new, re.I):
                raise ValueError(f"static child {child} needs {key} = .true. for the force/stress gates")
    F = re.findall(r"Total force =\s+([\d.]+)", out)
    P = re.findall(r"P=\s*(-?[\d.]+)", out)
    note = (f"{os.path.basename(parent_dir)} final coordinates (parent last Total force {F[-1] if F else '?'} Ry/bohr, "
            f"P {P[-1] if P else '?'} kbar); calc={calc}; kspacing={ksp}; mesh={mesh}")
    return new, cell, sym, frac, mesh, note


def build_variant(parent_dir, child, ksp, ov):
    txt = open(os.path.join(parent_dir, "pw.in")).read()
    cell, sym, frac = sg.read_input(txt)
    mesh = sg.kmesh(cell, ksp)
    txt = sub1(r"outdir\s*=\s*'[^']*'", f"outdir      = '{CFG.get('scratch', '/dev/shm/qe')}/{child}'", txt)
    txt = sub1(r"(K_POINTS\s+\{?automatic\}?\s*\n)\s*\d+\s+\d+\s+\d+\s+\d\s+\d\s+\d",
               lambda m: m.group(1) + "  {} {} {}  0 0 0".format(*mesh), txt)
    if "ecut" in ov:
        txt = sub1(r"ecutwfc\s*=\s*[\d.dDeE+-]+", f"ecutwfc     = {ov['ecut'][0]:.1f}", txt)
        txt = sub1(r"ecutrho\s*=\s*[\d.dDeE+-]+", f"ecutrho     = {ov['ecut'][1]:.1f}", txt)
    if "degauss" in ov:
        txt = sub1(r"degauss\s*=\s*[\d.dDeE+-]+", f"degauss     = {ov['degauss']}", txt)
    note = (f"{os.path.basename(parent_dir)} input geometry; one-parameter test overrides={ov}; kspacing={ksp}; "
            f"mesh={mesh}")
    return txt, cell, sym, frac, mesh, note


def outcome(d, calc):
    p = os.path.join(d, "pw.out")
    if not os.path.exists(p):
        return "FAIL(no output)"
    t = open(p, errors="replace").read()
    if "convergence NOT achieved" in t:
        return "FAIL(scf not converged)"
    if "Program stopped by user request" in t:
        return "FAIL(exit-file stop)"
    if "JOB DONE" not in t:
        return "FAIL(no JOB DONE)"
    if calc in ("vc-relax", "relax"):
        if "bfgs failed" in t:
            return "FAIL(bfgs failed)"
        if "bfgs converged" in t and "End final coordinates" in t:
            return "OK"
        if "The maximum number of steps has been reached" in t:
            return "FAIL(nstep reached)"
        return "FAIL(bfgs not converged)"
    return "OK" if "convergence has been achieved" in t else "FAIL(scf)"


def pick_npool(ranks, nk, min_per_pool):
    c = [d for d in range(1, ranks + 1) if ranks % d == 0 and d <= nk and ranks // d >= min_per_pool]
    return max(c) if c else 1


def free_disk_gib():
    paths = [p for p in ("/", HERE, CFG["scratch"]) if os.path.exists(p)]
    return min(shutil.disk_usage(p).free for p in paths) / 2**30


def step(st):
    busy = set()
    for n, j in list(st["jobs"].items()):                       # 1. reconcile running jobs
        if j["status"] != "RUNNING":
            continue
        d = os.path.join(HERE, n)
        if job_procs(d):
            busy.update(j["cpus"])
            continue
        try:
            os.waitpid(j["pid"], os.WNOHANG)
        except (ChildProcessError, OSError):
            pass
        res = outcome(d, j["calc"])
        j.update(status="DONE" if res == "OK" else "FAILED", result=res, end=time.time())
        open(os.path.join(d, "STATE"), "w").write(
            f"{j['status']} {res} {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n")
        log(f"END {n} {res} wall {(j['end'] - j['start']) / 3600:.2f} h cpus {j['cpus'][0]}-{j['cpus'][-1]}")
        relax = j["calc"] in ("vc-relax", "relax")
        if (res != "OK" and CFG["delete_scratch_failed"]) or (res == "OK" and relax and CFG["delete_scratch_done_relax"]) \
                or (res == "OK" and not relax and CFG["delete_scratch_done_static"]):
            shutil.rmtree(f"{CFG['scratch']}/{n}", ignore_errors=True)
            log(f"SCRATCH-DELETED {CFG['scratch']}/{n} (qsched.json policy)")
        save_state(st)
    for n, j in list(st["jobs"].items()):                       # 2. follow-ups (idempotent; gate failures block)
        if j["status"] != "DONE":
            continue
        try:
            kids = children(n, j)
        except ValueError as e:
            log(f"FOLLOWUP-ERROR {n}: {e}")
            continue
        for child, calc, ksp, ov in kids:
            if child in st["jobs"]:
                if st["jobs"][child].get("parent") != n and child not in j.get("collisions", []):
                    j.setdefault("collisions", []).append(child)
                    log(f"FOLLOWUP-ERROR name collision: {n} -> {child} already exists (parent "
                        f"{st['jobs'][child].get('parent')}); not overwritten")
                    save_state(st)
                continue
            try:
                d = os.path.join(HERE, n)
                txt, cell, sym, frac, mesh, note = (build_variant(d, child, ksp, ov) if ov is not None
                                                    else build_followup(d, child, calc, ksp))
                write_child(child, txt, cell, sym, frac, j, note)
                nk = nirr(cell, sym, frac, mesh)
            except Exception as e:
                tries = j.setdefault("fu_tries", {})
                tries[child] = tries.get(child, 0) + 1
                log(f"FOLLOWUP-ERROR {n} -> {child} try {tries[child]}: {e!r}")
                if "gate FAIL" in repr(e) or tries[child] >= 3:
                    st["jobs"][child] = dict(status="BLOCKED", priority=j["priority"], calc=calc, parent=n,
                                             result="structure gate FAIL" if "gate FAIL" in repr(e)
                                             else f"follow-up build failed 3x: {e!r}"[:200])
                save_state(st)
                continue
            chain = ov is None    # chain child (relax -> relax -> static) vs one-parameter test variant
            st["jobs"][child] = dict(status="PENDING", priority=j["priority"], calc=calc, ranks_max=j["ranks_max"],
                                     ranks_min=j["ranks_min"], min_per_pool=j.get("min_per_pool", 1), nirr=nk,
                                     parent=n, nat=j.get("nat"), formula=j.get("formula"), label=j.get("label"),
                                     gate=j.get("gate"),
                                     tests_on_child=chain and j.get("tests_on_child", False),
                                     tests=chain and calc == "scf" and j.get("tests_on_child", False))
            log(f"QUEUED {child} from {n} mesh {mesh} irr~{nk}")
            save_state(st)
    stop = os.path.join(HERE, "STOP")                           # 3. hard stops
    disk = free_disk_gib()
    mem = int(re.search(r"MemAvailable:\s+(\d+)", open("/proc/meminfo").read()).group(1)) / 2**20
    if (disk < CFG["min_free_disk_gib"] or mem < CFG["min_mem_gib"]) and not os.path.exists(stop):
        open(stop, "w").write(f"auto hard stop: free disk {disk:.1f} GiB, MemAvailable {mem:.1f} GiB\n")
        log(f"HARD-STOP disk {disk:.1f} GiB mem {mem:.1f} GiB -> no new launches")
    if os.path.exists(stop):
        return
    free = [c for c in range(int(CFG["ncpus"])) if c not in busy]                   # 4. launches in priority order
    for n, j in sorted(list(st["jobs"].items()), key=lambda kv: (kv[1]["priority"], kv[0])):
        if j["status"] != "PENDING":
            continue
        if j.get("parent") and st["jobs"][j["parent"]]["status"] != "DONE":
            continue
        d = os.path.join(HERE, n)
        live = job_procs(d)
        if live:
            cpus = sorted({c for _, cl in live for c in expand(cl)})
            j.update(status="RUNNING", pid=live[0][0], cpus=cpus, start=j.get("start", time.time()))
            free = [c for c in free if c not in cpus]
            log(f"ADOPT {n} pids {[p for p, _ in live]} cpus {cpus[0]}-{cpus[-1]}")
            save_state(st)
            continue
        if len(free) < j["ranks_min"]:
            continue
        ranks = min(j["ranks_max"], len(free))
        npool = pick_npool(ranks, j["nirr"], j.get("min_per_pool", 1))
        cpus, free = free[:ranks], free[ranks:]
        os.makedirs(f"{CFG['scratch']}/{n}", exist_ok=True)
        cmd = ["taskset", "-c", ",".join(map(str, cpus)), "mpirun", "--bind-to", "none", "-np", str(ranks),
               CFG["pw"], "-nk", str(npool), "-in", "pw.in"]
        j.update(status="RUNNING", cpus=cpus, ranks=ranks, npool=npool, start=time.time(), cmd=" ".join(cmd), pid=-1)
        save_state(st)                                          # recorded before Popen; adoption covers a crash
        with open(os.path.join(d, "pw.out"), "w") as fo, open(os.path.join(d, "pw.err"), "w") as fe:
            p = subprocess.Popen(cmd, cwd=d, stdout=fo, stderr=fe, stdin=subprocess.DEVNULL,
                                 env={**os.environ, **CONTAINER_ENV, **CFG.get("env", {})},
                                 start_new_session=True)
        j["pid"] = p.pid
        open(os.path.join(d, "STATE"), "w").write(
            f"RUNNING pid {p.pid} ranks {ranks} npool {npool} cpus {cpus[0]}-{cpus[-1]}\n")
        log(f"START {n} ranks {ranks} npool {npool} cpus {cpus[0]}-{cpus[-1]} pid {p.pid}")
        save_state(st)


def load_jobs(st):
    for j in json.load(open(os.path.join(HERE, "jobs.json"))):
        if set(j) <= {"_note"}:
            continue
        for k in ("name", "calc", "ranks", "priority", "nat", "nirr_est", "formula"):
            if k not in j:
                sys.exit(f"jobs.json entry {j.get('name', '?')}: missing required key '{k}' (see the docstring)")
        g = j.get("gate") or {}
        if j.get("label") and not (g.get("shells") and g.get("pair_angle")):
            sys.exit(f"jobs.json entry {j['name']}: label '{j['label']}' needs gate.shells and gate.pair_angle")
        if not os.path.isfile(os.path.join(HERE, j["name"], "pw.in")):
            sys.exit(f"jobs.json entry {j['name']}: {j['name']}/pw.in missing")
        st["jobs"].setdefault(j["name"], dict(
            status="PENDING", priority=j["priority"], calc=j["calc"], ranks_max=j["ranks"],
            ranks_min=j.get("ranks_min", max(4, j["ranks"] // 2)), nat=j["nat"],
            min_per_pool=j.get("min_per_pool", 6 if j["nat"] >= 40 else 1), nirr=j["nirr_est"], parent=None,
            formula=j["formula"], label=j.get("label"), gate=j.get("gate"), tests=j.get("tests", False),
            tests_on_child=j.get("tests_on_child", False)))


def run():
    if not os.path.isdir("/proc"):
        sys.exit("qsched.py run needs Linux /proc (run it on the box; use offline-test locally)")
    lock = open(os.path.join(HERE, ".lock"), "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("another qsched.py holds the lock; exiting", flush=True)
        return
    load_config()
    os.makedirs(CFG["scratch"], exist_ok=True)
    st = json.load(open(STATE)) if os.path.exists(STATE) else {"jobs": {}}
    load_jobs(st)
    chained = any(n.endswith(("_vrC", "_vrF")) for n in st["jobs"])
    if chained and "chain_spacing" not in CFG:
        sys.exit("qsched.json: chain_spacing required (jobs use the _vrC/_vrF chain)")
    if any(j.get("tests") or j.get("tests_on_child") for j in st["jobs"].values()) and not CFG.get("tests"):
        sys.exit("qsched.json: tests required (a job requests one-parameter tests)")
    save_state(st)
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    log(f"scheduler start pid {os.getpid()} jobs {len(st['jobs'])} cpus 0-{int(CFG['ncpus']) - 1} config {json.dumps(CFG)}")
    while True:
        try:
            step(st)
            if all(j["status"] in ("DONE", "FAILED", "BLOCKED", "MOVED") for j in st["jobs"].values()):
                log("all jobs finished; scheduler exits")
                return
        except Exception:
            log("LOOP-ERROR " + traceback.format_exc().replace("\n", " | "))
        time.sleep(LOOP_SECONDS)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd")
    sp.add_parser("run", help="start the scheduler loop (on the box)")
    t = sp.add_parser("offline-test", help="rebuild one follow-up input offline and print it")
    t.add_argument("parent")
    t.add_argument("child")
    t.add_argument("--calc", default="scf")
    t.add_argument("--spacing", type=float, required=True)
    t.add_argument("--formula")
    t.add_argument("--override", help='JSON, e.g. \'{"ecut": [80, 640]}\' or \'{"degauss": 0.005}\' or \'{}\'')
    t.add_argument("--scratch", default="/dev/shm/qe", help="outdir parent written into the rebuilt input")
    a = ap.parse_args()
    if sg.np is None:
        sys.exit("qsched.py needs numpy (for structure_gate): python3 -m pip install numpy")
    if a.cmd == "run":
        run()
    elif a.cmd == "offline-test":
        CFG["scratch"] = a.scratch
        if a.override is not None:
            ov = json.loads(a.override)
            txt, cell, sym, frac, mesh, note = build_variant(a.parent, a.child, a.spacing, ov)
        else:
            txt, cell, sym, frac, mesh, note = build_followup(a.parent, a.child, a.calc, a.spacing)
        ok, rep = gate(cell, sym, frac, {"formula": a.formula})
        print(f"# {note}\n# gate: {rep.splitlines()[-1]}\n{txt}", end="")
    else:
        ap.print_help()
        sys.exit(2)


if __name__ == "__main__":
    main()
