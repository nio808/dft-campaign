#!/usr/bin/env python3
"""Convergence-ladder analyser for pw.x outputs: energy per atom AND pressure from the stress tensor.

usage: conv_ladder.py --tol-mev-atom T_E --tol-kbar T_P LABEL=OUT [LABEL=OUT ...]   (ordered coarse -> tightest)
  e.g. conv_ladder.py --tol-mev-atom 1 --tol-kbar 1 70=c70/scf.out 80=c80/scf.out 90=c90/scf.out 120=c120/scf.out

Rule (declare it in GATES.md BEFORE the ladder runs; the tolerances are the project's cited choice, not defaults):
keep the FIRST label whose row and every tighter row lie within T_E meV/atom and T_P kbar of the tightest (last) row.
Pressure is computed from the Ry/bohr^3 tensor (1 Ry/bohr^3 = 147105.079 kbar), not the printed P (0.01 kbar
resolution), so print-resolution ties cannot decide a rule. Energies are the last '!' line (Ry); the atom count comes
from 'number of atoms/cell' and must be equal in every row. Exit 1 if a row is unreadable or no label passes.
"""
import argparse
import re
import sys

RY_MEV = 13605.693123
RY_BOHR3_KBAR = 147105.079


def read(path):
    t = open(path, errors="replace").read()
    e = re.findall(r"^!\s+total energy\s+=\s+(-?[\d.]+) Ry", t, re.M)
    nat = re.search(r"number of atoms/cell\s+=\s+(\d+)", t)
    if not e or not nat or "JOB DONE" not in t or "convergence NOT achieved" in t:
        raise ValueError(f"{path}: no converged '!' energy / atom count / JOB DONE")
    j = t.rfind("total   stress")
    p = None
    if j >= 0:
        rows = t[j:].splitlines()[1:4]
        try:
            p = sum(float(rows[i].split()[i]) for i in range(3)) / 3 * RY_BOHR3_KBAR
        except (ValueError, IndexError):
            p = None
    return float(e[-1]), int(nat.group(1)), p


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tol-mev-atom", type=float, required=True)
    ap.add_argument("--tol-kbar", type=float, required=True, help="use a large value only if stress is not computed")
    ap.add_argument("rows", nargs="+")
    a = ap.parse_args()
    data = []
    for r in a.rows:
        label, _, path = r.partition("=")
        try:
            data.append((label, path) + read(path))
        except ValueError as e:
            print("FAIL", e)
            sys.exit(1)
    nats = {d[3] for d in data}
    if len(nats) != 1:
        print(f"FAIL atom counts differ between rows: {sorted(nats)}")
        sys.exit(1)
    nat = nats.pop()
    eref, pref = data[-1][2], data[-1][4]
    print(f"{'label':>8s} {'E (Ry)':>16s} {'dE meV/atom':>12s} {'P kbar':>10s} {'dP kbar':>9s}  file")
    ok = []
    for label, path, e, _, p in data:
        de = (e - eref) * RY_MEV / nat
        dp = (p - pref) if (p is not None and pref is not None) else None
        passes = abs(de) <= a.tol_mev_atom and (dp is not None and abs(dp) <= a.tol_kbar)
        ok.append(passes)
        print(f"{label:>8s} {e:16.8f} {de:12.4f} {('%.4f' % p) if p is not None else '-':>10s} "
              f"{('%+.4f' % dp) if dp is not None else '-':>9s}  {path}")
    kept = next((data[i][0] for i in range(len(data)) if all(ok[i:])), None)
    print(f"rule: within {a.tol_mev_atom} meV/atom and {a.tol_kbar} kbar of '{data[-1][0]}', every tighter row too")
    print(f"KEPT {kept}" if kept else "NO LABEL PASSES (extend the ladder; do not loosen the rule silently)")
    sys.exit(0 if kept else 1)


if __name__ == "__main__":
    main()
