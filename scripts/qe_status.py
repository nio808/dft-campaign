#!/usr/bin/env python3
"""One-line status per QE job directory, plus ALERT flags and box health. Read-only; safe on the box or locally.

usage: qe_status.py DIR [DIR ...] [--out pw.out] [--ref KEY=E_REF[,KEY=E_REF]] [--atoms-per-fu N]
                    [--state state.json] [--stale 30] [--scheduler qsched.py]

Per job: state, SCF count, last '!' energy, dE per formula unit vs --ref (meV/f.u.), total force, pressure, |M|,
SCF iteration and estimated accuracy of the current SCF, eigenvalue warnings, output age.
--ref keys match the job directory name as '_<key>_' or as a substring; energies are Ry per formula unit, and
formula units = number of atoms / --atoms-per-fu.
--state reads a qsched.py state.json for scheduler status/results; otherwise state is inferred from the output
(relax/vc-relax runs are recognised from the output, so --out vc-relax.out works without a pw.in).
--schedlog sched.log adds ALERT-SCHEDLOG for LOOP-ERROR / HARD-STOP / FOLLOWUP-ERROR lines from the last hour.
Alerts: ALERT-STALE (running, no write for > --stale min), ALERT-FAILED/BLOCKED (scheduler), ALERT-RESULT (a FAIL
result without scheduler state, e.g. bfgs failed / not converged), ALERT-SCHEDLOG, ALERT-NOTCONV
(convergence NOT achieved), ALERT-EXITSTOP (stopped by user request: JOB DONE is not convergence), ALERT-NSTEP,
ALERT-NOJOBDONE (stopped writing without JOB DONE), ALERT-SLOSH (accuracy not improving after 60 iterations),
ALERT-EIGWARN (eigenvalues not converged in a bands/nscf run), ALERT-SCHEDULER-DEAD (only while jobs are PENDING or
RUNNING), ALERT-MEM (MemAvailable < --mem-alert-gib, default 15),
ALERT-DISK (free on / < --disk-alert-gib, default 5).
Exit 0 always (the watcher greps for ALERT).
"""
import argparse
import calendar
import json
import os
import re
import shutil
import time

RY_MEV = 13605.693123


def parse_out(t):
    r = {}
    r["E"] = re.findall(r"^!\s+total energy\s+=\s+(-?[\d.]+) Ry", t, re.M)
    nat = re.search(r"number of atoms/cell\s+=\s+(\d+)", t)
    r["nat"] = int(nat.group(1)) if nat else None
    r["F"] = re.findall(r"Total force =\s+([\d.]+)", t)
    r["P"] = re.findall(r"P=\s*(-?[\d.]+)", t)
    r["M"] = re.findall(r"absolute magnetization\s+=\s+(-?[\d.]+)", t)
    last_scf = t.rsplit("Self-consistent Calculation", 1)[-1]
    r["it"] = re.findall(r"iteration #\s*(\d+)", last_scf)
    r["acc"] = [float(x) for x in re.findall(r"estimated scf accuracy\s+<\s+([\d.Ee+-]+)", last_scf)]
    r["done"] = "JOB DONE" in t
    r["notconv"] = "convergence NOT achieved" in t or "No convergence has been achieved" in t  # pw.x / ph.x
    r["exitstop"] = "Program stopped by user request" in t
    r["nstep"] = "maximum number of steps has been reached" in t
    r["bfgs"] = "bfgs converged" in t and "End final coordinates" in t
    r["bfgsfail"] = "bfgs failed" in t
    r["relax"] = "BFGS Geometry Optimization" in t   # relax / vc-relax, detected from the output itself
    r["scfok"] = "convergence has been achieved" in t
    r["eigwarn"] = len(re.findall(r"eigenvalues not converged", t))
    # Early-SCF Davidson warnings are harmless; they matter for band-structure / non-SCF runs (published bands).
    r["nonscf"] = "Band Structure Calculation" in t or "End of band structure calculation" in t
    r["nosym"] = "No symmetry found" in t
    return r


def outcome(r, relax_expected):
    if r["notconv"]:
        return "FAIL(scf not converged)"
    if r["exitstop"]:
        return "STOPPED(exit file)"
    if not r["done"]:
        return ""
    if r["nonscf"]:   # bands / nscf: no SCF loop; success = JOB DONE without non-convergence
        return "OK"
    if relax_expected or r["relax"]:
        if r["bfgsfail"]:
            return "FAIL(bfgs failed)"
        if r["bfgs"]:
            return "OK"
        return "FAIL(nstep)" if r["nstep"] else "FAIL(bfgs not converged)"
    return "OK" if r["scfok"] else "FAIL(scf)"


def ref_for(name, refs):
    for k, v in refs.items():
        if f"_{k}_" in name:
            return v
    for k, v in refs.items():
        if k in name:
            return v
    return None


def sched_alive(name):
    if not os.path.isdir("/proc"):
        return None
    for p in filter(str.isdigit, os.listdir("/proc")):
        try:
            a = open(f"/proc/{p}/cmdline", "rb").read().split(b"\0")
        except OSError:
            continue
        if len(a) > 1 and b"python" in a[0] and a[1].endswith(name.encode()):
            return True
    return False


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--out", default="pw.out")
    ap.add_argument("--ref", default="")
    ap.add_argument("--atoms-per-fu", type=int, default=0)
    ap.add_argument("--state")
    ap.add_argument("--stale", type=float, default=30.0)
    ap.add_argument("--mem-alert-gib", type=float, default=15.0, help="ALERT-MEM below this MemAvailable")
    ap.add_argument("--disk-alert-gib", type=float, default=5.0, help="ALERT-DISK below this free space on /")
    ap.add_argument("--scheduler")
    ap.add_argument("--schedlog", help="scheduler log to scan for LOOP-ERROR/HARD-STOP/FOLLOWUP-ERROR in the last hour")
    a = ap.parse_args()
    refs = {k: float(v) for k, v in (x.split("=") for x in a.ref.split(",") if "=" in x)}
    st = json.load(open(a.state))["jobs"] if a.state and os.path.isfile(a.state) else {}
    now = time.time()
    print(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), end="")
    if a.scheduler:
        alive = sched_alive(a.scheduler)
        unfinished = any(j.get("status") in ("PENDING", "RUNNING") for j in st.values()) if st else True
        word = {True: "ALIVE", None: "n/a (no /proc)",
                False: "NOT RUNNING" + (" ALERT-SCHEDULER-DEAD" if unfinished else " (all jobs finished)")}[alive]
        print(" scheduler", word, end="")
    print()
    if a.schedlog and os.path.isfile(a.schedlog):
        for l in open(a.schedlog, errors="replace").read().splitlines()[-300:]:
            if any(k in l for k in ("LOOP-ERROR", "HARD-STOP", "FOLLOWUP-ERROR")):
                try:
                    ts = calendar.timegm(time.strptime(l[:20], "%Y-%m-%dT%H:%M:%SZ"))
                except ValueError:
                    continue
                if now - ts < 3600:
                    print("ALERT-SCHEDLOG", l[:300])
    for d in a.dirs:
        if not os.path.isdir(d):
            continue
        name = os.path.basename(os.path.normpath(d))
        out = os.path.join(d, a.out)
        if name.startswith(("_", ".")) or (name not in st and not os.path.exists(out)
                                           and not os.path.exists(os.path.join(d, "pw.in"))):
            continue
        t = open(out, errors="replace").read() if os.path.exists(out) else ""
        r = parse_out(t)
        inp = os.path.join(d, "pw.in")
        relax_expected = False
        if os.path.exists(inp):
            m = re.search(r"calculation\s*=\s*'([^']+)'", open(inp, errors="replace").read())
            relax_expected = bool(m and m.group(1) in ("relax", "vc-relax"))
        age = (now - os.path.getmtime(out)) / 60 if os.path.exists(out) else -1
        j = st.get(name, {})
        res = outcome(r, relax_expected)
        state = j.get("status") or ("DONE" if r["done"] else ("RUNNING" if 0 <= age <= a.stale else
                                                             ("STALLED" if t else "PENDING")))
        result = j.get("result") or res
        rel = "       -"
        ref = ref_for(name, refs)
        if r["E"] and r["nat"] and a.atoms_per_fu and ref is not None:
            nfu = r["nat"] / a.atoms_per_fu
            rel = f"{(float(r['E'][-1]) / nfu - ref) * RY_MEV:+8.2f}"
        flags = []
        if j and state == "RUNNING" and age > a.stale:
            flags.append(f"ALERT-STALE({age:.0f}min)")
        if not j and t and not r["done"] and age > a.stale:
            flags.append(f"ALERT-NOJOBDONE({age:.0f}min: stalled or died)")
        if state in ("FAILED", "BLOCKED") and not str(result).startswith("STOPPED("):
            flags.append(f"ALERT-{state}")
        elif str(result).startswith("FAIL"):
            flags.append("ALERT-RESULT")
        if r["notconv"]:
            flags.append("ALERT-NOTCONV")
        if r["exitstop"]:
            flags.append("ALERT-EXITSTOP")
        if r["nstep"]:
            flags.append("ALERT-NSTEP")
        if not r["done"] and len(r["acc"]) >= 60 and min(r["acc"][-10:]) >= 0.5 * min(r["acc"][-30:-10]):
            flags.append("ALERT-SLOSH")
        if r["eigwarn"] and r["nonscf"]:
            flags.append(f"ALERT-EIGWARN({r['eigwarn']})")
        el = ""
        if j.get("start"):
            el = f"{(j.get('end', now) - j['start']) / 3600:5.2f}h "
        print(f"{name:38s} {state:8s} {str(result):24s} {el}nSCF {len(r['E']):3d} "
              f"E {r['E'][-1] if r['E'] else '-':>16s} dE/fu {rel} F {r['F'][-1] if r['F'] else '-':>9s} "
              f"P {r['P'][-1] if r['P'] else '-':>7s} |M| {r['M'][-1] if r['M'] else '-':>5s} "
              f"it {r['it'][-1] if r['it'] else '-':>3s} acc {r['acc'][-1] if r['acc'] else '-'} "
              f"{'nosym ' if r['nosym'] else ''}age {age:.0f}m {' '.join(flags)}".rstrip())
    health = []
    if os.path.isfile("/proc/meminfo"):
        mem = int(re.search(r"MemAvailable:\s+(\d+)", open("/proc/meminfo").read()).group(1)) / 2**20
        health.append(f"MemAvailable {mem:.1f} GiB" + (" ALERT-MEM" if mem < a.mem_alert_gib else ""))
        health.append("load " + " ".join(open("/proc/loadavg").read().split()[:3]))
    for mnt in ("/", "/dev/shm"):
        if os.path.isdir(mnt):
            u = shutil.disk_usage(mnt)
            free = u.free / 2**30
            health.append(f"{mnt} free {free:.1f} GiB" + (" ALERT-DISK" if free < a.disk_alert_gib and mnt == "/" else ""))
    if health:
        print(" | ".join(health))


if __name__ == "__main__":
    main()
