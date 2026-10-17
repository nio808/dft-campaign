#!/usr/bin/env python3
"""Force and stress gate on pw.x outputs (generalised from Project M's fcheck.py after two review findings).

usage: fcheck.py FMAX SMAX DMAX_F DMAX_S REF.out [OTHER.out ...]
  FMAX    bound on every Cartesian force component of every output (Ry/bohr)
  SMAX    bound on every stress component of every output (kbar)
  DMAX_F  bound on |F_other - F_ref| per component (Ry/bohr); DMAX_S bound on |sigma_other - sigma_ref| (kbar)
Uses the LAST force block and the LAST stress tensor of each file; the atom count comes from
"number of atoms/cell". Every atom must appear exactly once with finite values, else the file is rejected.
Typical: fcheck.py 1e-4 0.5 1e-4 0.5 tight.out highcut.out dense.out
Self-test: fcheck.py --check   (synthetic outputs: passes a good file, rejects a missing atom, NaN, a tighter bound)
Exit 1 if any bound is broken or any record is malformed.
"""
import os
import re
import sys
import tempfile

try:
    import numpy as np
except ImportError:  # --help and usage must still work without numpy
    np = None


def read(path):
    txt = open(path, errors="replace").read()
    m = re.search(r"number of atoms/cell\s+=\s+(\d+)", txt)
    if not m:
        raise AssertionError(f"{path}: no 'number of atoms/cell'")
    nat = int(m.group(1))
    i = txt.rfind("Forces acting on atoms")
    if i < 0:
        raise AssertionError(f"{path}: no force block (tprnfor?)")
    blk = txt[i:].split("Total force")[0]
    # verbosity='high' repeats atom lines for each force contribution after the total block: take the first nat
    rows = re.findall(r"atom\s+(\d+)\s+type\s+\d+\s+force =\s+(\S+)\s+(\S+)\s+(\S+)", blk)[:nat]
    idx = sorted(int(r[0]) for r in rows)
    if idx != list(range(1, nat + 1)):
        raise AssertionError(f"{path}: force block atoms {idx[:5]}... != 1..{nat}")
    f = np.array([[float(x) for x in r[1:]] for r in sorted(rows, key=lambda r: int(r[0]))])
    j = txt.rfind("total   stress")
    if j < 0:
        raise AssertionError(f"{path}: no stress tensor (tstress?)")
    st = txt[j:].splitlines()[1:4]
    s = np.array([[float(x) for x in l.split()[3:6]] for l in st])
    if f.shape != (nat, 3) or s.shape != (3, 3) or not (np.isfinite(f).all() and np.isfinite(s).all()):
        raise AssertionError(f"{path}: malformed or non-finite forces/stress")
    return f, s


def gate(fmax, smax, dmf, dms, paths):
    ref_f, ref_s = read(paths[0])
    bad = False
    for p in paths:
        f, s = read(p)
        if f.shape != ref_f.shape:
            raise AssertionError(f"{p}: atom count differs from {paths[0]}")
        df, ds = abs(f - ref_f).max(), abs(s - ref_s).max()
        ok = abs(f).max() < fmax and abs(s).max() < smax and df < dmf and ds < dms
        bad |= not ok
        print(f"{'ok  ' if ok else 'FAIL'} {p}: max|F| {abs(f).max():.2e}  max|sigma| {abs(s).max():.2f} kbar"
              f"  max|dF| {df:.2e}  max|dsigma| {ds:.2f} kbar  (atoms {len(f)})")
    return bad


def _fake(nat=3, nan=False, drop=None, big=False, high=False):
    lines = ["     number of atoms/cell      =            %d" % nat, "", "     Forces acting on atoms (cartesian axes, Ry/au):", ""]
    for a in range(1, nat + 1):
        if a == drop:
            continue
        v = "nan" if (nan and a == nat) else ("0.00050000" if big else "0.00001000")
        lines.append(f"     atom    {a} type  1   force =     {v}   -0.00002000    0.00000000")
    if high:   # verbosity='high': contribution blocks repeat the atom lines before "Total force"
        lines += ["", "     The non-local contrib.  to forces"]
        lines += [f"     atom    {a} type  1   force =     0.10000000    0.10000000    0.10000000" for a in range(1, nat + 1)]
    lines += ["", "     Total force =     0.000030     Total SCF correction =     0.000001", "",
              "     Computing stress (Cartesian axis) and pressure", "",
              "          total   stress  (Ry/bohr**3)                   (kbar)     P=        0.03",
              "   0.00000020   0.00000000   0.00000000            0.03        0.00        0.00",
              "   0.00000000   0.00000020   0.00000000            0.00        0.03        0.00",
              "   0.00000000   0.00000000   0.00000020            0.00        0.00        0.03", "", "JOB DONE."]
    fd, p = tempfile.mkstemp(suffix=".out")
    os.close(fd)
    open(p, "w").write("\n".join(lines) + "\n")
    return p


def selftest():
    good, big, high = _fake(), _fake(big=True), _fake(high=True)
    try:
        assert not gate(1e-4, 0.5, 1e-4, 0.5, [good, good]), "good file failed"
        assert not gate(1e-4, 0.5, 1e-4, 0.5, [good, high]), "verbosity='high' file failed"
        assert gate(1e-5, 0.5, 1e-4, 0.5, [good]), "tighter force bound passed"
        assert gate(1e-4, 0.5, 1e-4, 0.5, [good, big]), "large force passed"
        for bad in (_fake(drop=2), _fake(nan=True)):
            try:
                read(bad)
                raise SystemExit(f"malformed record accepted: {bad}")
            except AssertionError:
                pass
            finally:
                os.remove(bad)
    finally:
        for f in (good, big, high):
            os.remove(f)
    print("check passed")


if __name__ == "__main__":
    if len(sys.argv) < 6 or sys.argv[1] in ("-h", "--help"):
        if sys.argv[1:] != ["--check"]:
            print(__doc__)
            sys.exit(0 if sys.argv[1:2] in (["-h"], ["--help"]) else 2)
    if np is None:
        sys.exit("fcheck.py needs numpy: python3 -m pip install numpy")
    if sys.argv[1:] == ["--check"]:
        selftest()
        sys.exit(0)
    a = sys.argv[1:]
    try:
        sys.exit(gate(float(a[0]), float(a[1]), float(a[2]), float(a[3]), a[4:]))
    except AssertionError as e:
        print("FAIL", e)
        sys.exit(1)
