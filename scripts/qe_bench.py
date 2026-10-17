#!/usr/bin/env python3
"""Benchmark table from finished Quantum ESPRESSO outputs (pw.x and ph.x): parallel layout, size, wall time, per-host
summary, and a same-input comparison across hosts. Reads text outputs only; runs nothing.

usage: qe_bench.py [--host LABEL=REGEX ...] [--map hosts.json] [--cores LABEL=N ...] [--exclude REGEX ...]
                   [--csv out.csv] ROOT [ROOT ...]
  --host   assign outputs whose path matches REGEX to host LABEL (first match wins; repeatable)
  --map    JSON list of [REGEX, LABEL] or [REGEX, LABEL, CORES] entries, same meaning (for many hosts)
  --cores  usable cores of a host (physical cores, or the cgroup quota if lower): enables the capacity check
  --exclude  skip paths matching REGEX (repeatable; .save/ tmp/ SAVE/ are always skipped)
  --min-iters N   rows with fewer SCF iterations are left out of the timing summaries (default 5)
Unmatched outputs get host 'unassigned'. QE does not print the hostname, so the map is the provenance: record it.

Counting rules (an earlier version over-counted by about 25%): copies of one run (identical file, or the same
start time, wall time, atoms and k points in two folders: mirrors, snapshots, post-processing dirs) count once. Runs that were killed
print no wall time and are not counted, so every total here is a floor. Units, reported side by side:
  busy h  hours during which at least one job ran on that host (machine-hours of real work, not rental hours)
  rank-h  sum of wall x ranks x threads (what the jobs asked for)
  core-h  core-time used: rank-h, but never more than the host's usable cores at any instant (not capacity); needs --cores
  peak    most ranks running at once; peak > cores means oversubscription (or clock skew between outputs)

Per row: program, version, kind (scf / relax / vc-relax / nscf-bands / ph.x), MPI ranks, threads, pools, ranks per
pool, atoms, k points, bands, cutoffs, spin, FFT grid, SCF iterations, '!' cycles, wall seconds, JOB DONE, and
  s_per_iter      = wall / SCF iterations (includes setup, forces and stress: a layout metric, not a kernel timing)
  core_s_per_k_it = wall * ranks * threads / (iterations * k points)   (compare boxes only on IDENTICAL inputs)
Matched-shape table: rows sharing (program, atoms, k points, bands, cutoffs, spin, FFT grid) on two or more hosts,
an indicative per-core comparison. Mixed-input medians across hosts are not a speed ranking; they are labelled so.
"""
import argparse
import collections
import csv
import datetime as dt
import hashlib
import json
import os
import re
import statistics
import sys

ALWAYS_SKIP = re.compile(r"(\.save/|/tmp/|/SAVE/)")
UNIT = {"d": 86400, "h": 3600, "m": 60, "s": 1}


def tsec(s):
    return sum(float(v) * UNIT[u] for v, u in re.findall(r"([\d.]+)\s*([dhms])", s))


def grab(pat, t, cast=str):
    m = re.search(pat, t, re.M)
    return cast(m.group(1)) if m else None


def parse(path):
    try:
        t = open(path, errors="replace").read()
    except OSError:
        return None
    prog = grab(r"Program (PWSCF|PHONON) v", t)
    if not prog:
        return None
    walls = re.findall(r"^\s+(?:PWSCF|PHONON)\s+:.*CPU\s+(.*?)\s+WALL", t, re.M)
    st = re.search(r"starts on\s+(\d+)\s*(\w{3})\s*(\d{4}) at\s+([\d ]+):\s*([\d ]+):\s*([\d ]+)", t)
    try:
        start = dt.datetime.strptime("{} {} {} {}:{}:{}".format(*[g.strip() for g in st.groups()]),
                                     "%d %b %Y %H:%M:%S") if st else None
    except ValueError:
        start = None
    ram = re.search(r"Estimated max dynamical RAM per process >\s+([\d.]+) ([MG])B", t)
    if prog == "PHONON":
        kind = "ph.x"
    elif "End of band structure calculation" in t or "Band Structure Calculation" in t:
        kind = "nscf-bands"
    elif "BFGS Geometry Optimization" in t:
        kind = "vc-relax" if "new unit-cell volume" in t else "relax"
    else:
        kind = "scf"
    np_ = grab(r"running on\s+(\d+) processors", t, int) or grab(r"Number of MPI processes:\s+(\d+)", t, int) or 1
    npool = grab(r"npool\s+=\s+(\d+)", t, int) or 1
    r = dict(path=path, prog=prog, version=grab(r"Program (?:PWSCF|PHONON) v\.?([\d.]+)", t), kind=kind,
             ranks=np_, threads=grab(r"Threads/MPI process:\s+(\d+)", t, int) or 1, pools=npool,
             ranks_per_pool=np_ // npool if npool else np_,
             nat=grab(r"number of atoms/cell\s+=\s+(\d+)", t, int),
             nks=grab(r"number of k points=\s+(\d+)", t, int),
             nbnd=grab(r"number of Kohn-Sham states=\s+(\d+)", t, int),
             ecutwfc=grab(r"kinetic-energy cutoff\s+=\s+([\d.]+)", t, float),
             ecutrho=grab(r"charge density cutoff\s+=\s+([\d.]+)", t, float),
             spin="lsda" if ("Starting magnetic structure" in t or "total magnetization" in t) else "none",
             fft=(grab(r"Dense\s+grid:\s+\d+ G-vectors\s+FFT dimensions: \(\s*([\d ,]+)\)", t) or "").replace(" ", ""),
             ram_gb_per_rank=round(float(ram.group(1)) / (1024 if ram.group(2) == "M" else 1), 3) if ram else None,
             iters=len(re.findall(r"^\s+iteration #\s*\d+", t, re.M)),
             scf_cycles=len(re.findall(r"^!", t, re.M)),
             wall_s=round(tsec(walls[-1]), 2) if walls else None,
             start=start.isoformat(sep=" ") if start else None,
             sha256=hashlib.sha256(t.encode("utf-8", "replace")).hexdigest(),
             job_done="JOB DONE" in t,
             stopped="Program stopped by user request" in t)
    if r["wall_s"] and r["iters"]:
        r["s_per_iter"] = round(r["wall_s"] / r["iters"], 3)
        if r["nks"]:
            r["core_s_per_k_it"] = round(r["wall_s"] * r["ranks"] * r["threads"] / (r["iters"] * r["nks"]), 4)
    return r


def size_bucket(n):
    if n is None:
        return "?"
    for hi, lab in ((10, "<=10"), (20, "11-20"), (30, "21-30"), (45, "31-45"), (80, "46-80")):
        if n <= hi:
            return lab
    return ">80"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("roots", nargs="*")
    ap.add_argument("--host", action="append", default=[], metavar="LABEL=REGEX")
    ap.add_argument("--map")
    ap.add_argument("--cores", action="append", default=[], metavar="LABEL=N")
    ap.add_argument("--exclude", action="append", default=[])
    ap.add_argument("--csv")
    ap.add_argument("--min-iters", type=int, default=5)
    a = ap.parse_args()
    if not a.roots:
        ap.print_help()
        sys.exit(0)
    hosts, cores = [], {}
    if a.map:
        for e in json.load(open(a.map)):
            hosts.append((re.compile(e[0]), e[1]))
            if len(e) > 2 and e[2]:
                cores[e[1]] = int(e[2])
    for h in a.host:
        lab, _, rx = h.partition("=")
        if not rx:
            sys.exit(f"--host needs LABEL=REGEX, got {h!r}")
        hosts.append((re.compile(rx), lab))
    for c in a.cores:
        lab, _, n = c.partition("=")
        cores[lab] = int(n)
    excl = [re.compile(x) for x in a.exclude]
    found = []
    for root in a.roots:
        for dp, dn, fn in os.walk(root):
            dn[:] = [d for d in dn if not d.endswith(".save") and d not in ("tmp", "SAVE", ".git")]
            for f in fn:
                if not (f.endswith(".out") or ".out." in f or f.startswith(("pw.out", "ph.out"))):
                    continue
                p = os.path.join(dp, f)
                if ALWAYS_SKIP.search(p) or any(x.search(p) for x in excl) or os.path.getsize(p) < 1500:
                    continue
                r = parse(p)
                if r:
                    r["host"] = next((lab for rx, lab in hosts if rx.search(p)), "unassigned")
                    found.append(r)
    if not found:
        sys.exit("no pw.x / ph.x outputs found")
    order = {lab: i for i, (_, lab) in enumerate(hosts)}
    rows, seen, cross = [], {}, []
    for r in sorted(found, key=lambda r: (order.get(r["host"], len(order)), r["path"])):
        run_id = (r["start"], r["wall_s"], r["nat"], r["nks"]) if r["start"] else None
        kept = seen.get(r["sha256"]) or (seen.get(run_id) if run_id else None)
        if kept:
            if kept["host"] != r["host"]:
                cross.append((kept, r))
            continue
        seen[r["sha256"]] = r
        if run_id:
            seen[run_id] = r
        rows.append(r)
    print(f"{len(found)} outputs, {len(found) - len(rows)} copies of the same run dropped, {len(rows)} runs; "
          f"{sum(1 for r in rows if not r['wall_s'])} without a wall time (killed or still running) are not timed")
    if cross:
        print(f"{len(cross)} copies sit under a different host's folder than the kept one (kept = first host in map "
              f"order; fix the map or --exclude the copy folders if that is wrong), e.g.:")
        for k, c in cross[:5]:
            print(f"   kept {k['host']}: {k['path']}\n   copy {c['host']}: {c['path']}")
    if a.csv:
        cols = ["host", "prog", "version", "kind", "nat", "nks", "nbnd", "ecutwfc", "ecutrho", "spin", "fft",
                "ranks", "threads", "pools", "ranks_per_pool", "iters", "scf_cycles", "start", "wall_s", "s_per_iter",
                "core_s_per_k_it", "ram_gb_per_rank", "job_done", "stopped", "path"]
        with open(a.csv, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        print(f"wrote {len(rows)} rows to {a.csv}")

    def spans(rs):
        out = []
        for r in rs:
            if r["start"] and r["wall_s"]:
                t0 = dt.datetime.fromisoformat(r["start"])
                out.append((t0, t0 + dt.timedelta(seconds=r["wall_s"]), r["ranks"] * r["threads"]))
        return out

    def union_hours(iv):
        tot, end = 0.0, None
        for t0, t1, _ in sorted(iv):
            if end is None or t0 > end:
                tot += (t1 - t0).total_seconds()
                end = t1
            elif t1 > end:
                tot += (t1 - end).total_seconds()
                end = t1
        return tot / 3600

    def load_profile(iv, cap):
        """(peak ranks, rank-h capped at cap at every instant)."""
        cuts = sorted({t for t0, t1, _ in iv for t in (t0, t1)})
        peak, capped = 0, 0.0
        for t0, t1 in zip(cuts, cuts[1:]):
            load = sum(n for s, e, n in iv if s <= t0 and e >= t1)
            peak = max(peak, load)
            capped += min(load, cap if cap else load) * (t1 - t0).total_seconds() / 3600
        return peak, capped

    by_host = collections.defaultdict(list)
    for r in rows:
        by_host[r["host"]].append(r)
    print(f"\n{'host':36s} {'runs':>5s} {'done':>5s} {'first start':>16s} {'busy h':>7s} {'rank-h':>7s} "
          f"{'cores':>5s} {'peak':>5s} {'core-h':>7s}")
    all_iv, tot_rank, tot_core, mach_h = [], 0.0, 0.0, 0.0
    for h, rs in sorted(by_host.items()):
        iv = spans(rs)
        all_iv += iv
        mach_h += union_hours(iv)
        rank_h = sum((t1 - t0).total_seconds() * n for t0, t1, n in iv) / 3600
        cap = cores.get(h)
        peak, capped = load_profile(iv, cap) if iv else (0, 0.0)
        tot_rank += rank_h
        tot_core += capped if cap else rank_h
        first = min(t0 for t0, _, _ in iv).strftime("%Y-%m-%d %H:%M") if iv else "-"
        flag = "  OVERSUBSCRIBED" if cap and peak > cap else ""
        print(f"{h[:36]:36s} {len(rs):5d} {sum(r['job_done'] for r in rs):5d} {first:>16s} {union_hours(iv):7.1f} "
              f"{rank_h:7.0f} {cap or '?':>5} {peak:5d} {(f'{capped:7.0f}' if cap else '      ?')}{flag}")
    busy = union_hours(all_iv)
    span = ((max(t1 for _, t1, _ in all_iv) - min(t0 for t0, _, _ in all_iv)).total_seconds() / 86400) if all_iv else 0
    print(f"busy wall-clock (any host computing a timed run): {busy:.1f} h within a {span:.1f}-day span; "
          f"machine-h {mach_h:.1f} (mean {mach_h / busy if busy else 0:.2f} hosts busy); rank-h {tot_rank:.0f}; "
          f"core-h used {tot_core:.0f}" + ("" if all(h in cores for h in by_host) else
                                            " (hosts without --cores counted at requested ranks)"))
    print("Start times are each machine's own clock; mixed time zones shift the calendar overlap, not per-host sums.")

    timed = [r for r in rows if r["prog"] == "PWSCF" and r["kind"] != "nscf-bands" and r.get("core_s_per_k_it")
             and r["iters"] >= a.min_iters]
    print(f"\npw.x timing by host and cell size (MIXED inputs: describes the workload, not a speed ranking; "
          f"rows with >= {a.min_iters} SCF iterations)")
    print(f"{'host':40s} {'atoms':>6s} {'n':>4s} {'ranks':>7s} {'ranks/pool (count)':>22s} {'s/iter':>8s} "
          f"{'core-s/(k it)':>13s}")
    grp = collections.defaultdict(list)
    for r in timed:
        grp[(r["host"], size_bucket(r["nat"]))].append(r)
    order = ["<=10", "11-20", "21-30", "31-45", "46-80", ">80", "?"]
    for (h, b) in sorted(grp, key=lambda k: (k[0], order.index(k[1]))):
        rs = grp[(h, b)]
        rpp = ", ".join(f"{k}({v})" for k, v in collections.Counter(r["ranks_per_pool"] for r in rs).most_common(2))
        print(f"{h[:40]:40s} {b:>6s} {len(rs):4d} {min(r['ranks'] for r in rs):3d}-{max(r['ranks'] for r in rs):<3d} "
              f"{rpp:>22s} {statistics.median(r['s_per_iter'] for r in rs):8.1f} "
              f"{statistics.median(r['core_s_per_k_it'] for r in rs):13.3f}")

    fp = collections.defaultdict(list)
    for r in timed:
        fp[(r["prog"], r["nat"], r["nks"], r["nbnd"], r["ecutwfc"], r["ecutrho"], r["spin"], r["fft"])].append(r)
    same = {k: v for k, v in fp.items() if len({r["host"] for r in v}) >= 2}
    print(f"\nmatched-shape comparison (same atoms, k points, bands, cutoffs, spin and FFT grid on >= 2 hosts; the "
          f"geometry and SCF path may differ, so treat it as indicative and confirm with one identical input): "
          f"{len(same)} group(s)")
    for k, rs in sorted(same.items(), key=lambda kv: (kv[0][1] or 0)):
        print(f"  nat {k[1]} k {k[2]} bands {k[3]} ecut {k[4]}/{k[5]} spin {k[6]} FFT {k[7]}")
        for h in sorted({r["host"] for r in rs}):
            hr = [r for r in rs if r["host"] == h]
            print(f"    {h[:44]:44s} n={len(hr):3d} ranks {sorted({r['ranks'] for r in hr})} "
                  f"pools {sorted({r['pools'] for r in hr})} core-s/(k it) "
                  f"{statistics.median(r['core_s_per_k_it'] for r in hr):.3f}  s/iter "
                  f"{statistics.median(r['s_per_iter'] for r in hr):.2f}")


if __name__ == "__main__":
    main()
