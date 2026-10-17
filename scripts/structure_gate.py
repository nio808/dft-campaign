#!/usr/bin/env python3
"""Structure gate for QE inputs/outputs: formula per f.u., symmetry, distances, coordination shells (periodic images),
bridge angles, k mesh from a spacing rule. Prints FORMULA-CHECK.md text; exit 1 on GATE FAIL.

usage: structure_gate.py --check      (self-test on a built-in cubic perovskite)
       structure_gate.py FILE [--final | --evaluated] [--input PW.IN] [--formula FORMULA]
                         [--shell Ta:O,N:6[:RMAX]] [--expect-shell O4N2] [--pair-angle N] [--expect-label cis|trans]
                         [--cis-cut 135] [--bridge Ta:O:Ta] [--kspacing 0.2] [--expect-sg P4/mmm|123] [--expect-nops 6]
                         [--min-dist 0.6] [--write-cards OUT]
  FILE        a pw.x input (ibrav=0) or, with --final/--evaluated, a pw.x output
  --final     geometry of the last "Begin final coordinates" block (finished relax / vc-relax)
  --evaluated geometry printed before the LAST '!' energy (the last geometry actually evaluated; restart point after a
              stopped or migrated relaxation). Falls back to --input when the last '!' belongs to the starting geometry.
  --input     pw.x input supplying the cell for fixed-cell relax outputs and for the fallback above
  --shell     centre:ligands:N[:RMAX] — the N nearest ligand atoms of every centre atom (27+ periodic images)
  --expect-shell composition every shell must have, e.g. O4N2; --pair-angle X: angle X-centre-X of the two X in the
              shell, labelled cis (< --cis-cut) or trans; --expect-label requires that label for every centre
  --bridge    A:X:B — angle A-X-B at every X between its nearest A and nearest B (octahedral bridge/tilt angles)
  --kspacing  mesh n_i = max(1, ceil(|b_i| / spacing)), |b_i| in 1/Å including 2π (the spacing itself is a cited project choice)
Library use: from structure_gate import read_input, read_output, analyse
"""
import argparse
import math
import re
import sys

try:
    import numpy as np
except ImportError:  # --help and usage must still work without numpy
    np = None

BOHR = 0.529177210903


ELEMENTS = set("""H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr
Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir
Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr""".split())


def element(label):
    """Element of a QE species label: 'Ca', 'Ca1', 'CA', 'Fe_up', 'O2' -> Ca, Ca, Ca, Fe, O."""
    letters = re.match(r"[A-Za-z]+", label)
    if not letters:
        return label
    w = letters.group(0)
    two = w[:2].capitalize()
    if len(w) >= 2 and two in ELEMENTS:
        return two
    return w[0].upper()


def parse_formula(s):
    d = {}
    for el, n in re.findall(r"([A-Z][a-z]?)(\d*\.?\d*)", s):
        d[el] = d.get(el, 0) + (float(n) if n else 1.0)
    return d


def _cell_block(lines, unit, alat_bohr):
    v = np.array([[float(x) for x in l.split()[:3]] for l in lines[:3]])
    if unit.startswith("bohr"):
        return v * BOHR
    if unit.startswith("alat"):
        if not alat_bohr:
            raise ValueError("CELL_PARAMETERS alat needs celldm(1) or A")
        return v * alat_bohr * BOHR
    return v  # angstrom


def _positions(lines, unit, cell, alat_bohr, nat=None):
    sym, xyz = [], []
    for l in lines:
        p = l.split()
        if len(p) < 4 or not re.match(r"^[A-Z][A-Za-z0-9_]*$", p[0]):
            break
        sym.append(p[0])
        xyz.append([float(x.replace("d", "e").replace("D", "e")) for x in p[1:4]])
        if nat and len(sym) == nat:
            break
    if nat and len(sym) != nat:
        raise ValueError(f"ATOMIC_POSITIONS has {len(sym)} atoms, expected nat={nat}")
    xyz = np.array(xyz)
    if unit.startswith("crystal"):
        frac = xyz
    else:
        if unit.startswith("bohr"):
            cart = xyz * BOHR
        elif unit.startswith("alat"):
            cart = xyz * alat_bohr * BOHR
        else:
            cart = xyz
        frac = cart @ np.linalg.inv(cell)
    return sym, frac


def read_input(text):
    body = re.sub(r"!.*", "", text)
    ibrav = re.search(r"ibrav\s*=\s*(-?\d+)", body)
    if ibrav and int(ibrav.group(1)) != 0:
        raise ValueError("only ibrav=0 inputs are supported; write CELL_PARAMETERS explicitly")
    nat = int(re.search(r"nat\s*=\s*(\d+)", body).group(1))
    alat = None
    m = re.search(r"celldm\(1\)\s*=\s*([\d.eEdD+-]+)", body)
    if m:
        alat = float(m.group(1).replace("d", "e").replace("D", "e"))
    m = re.search(r"(?<![\w(])A\s*=\s*([\d.eEdD+-]+)", body)
    if m and alat is None:
        alat = float(m.group(1).replace("d", "e")) / BOHR
    lines = body.splitlines()
    ci = next(i for i, l in enumerate(lines) if l.strip().upper().startswith("CELL_PARAMETERS"))
    cunit = re.sub(r"[{}()=\s]", " ", lines[ci].strip()[15:]).strip().lower() or "alat"
    cell = _cell_block([l for l in lines[ci + 1:] if l.strip()], cunit, alat)
    pi = next(i for i, l in enumerate(lines) if l.strip().upper().startswith("ATOMIC_POSITIONS"))
    punit = re.sub(r"[{}()=\s]", " ", lines[pi].strip()[16:]).strip().lower() or "alat"
    sym, frac = _positions([l for l in lines[pi + 1:] if l.strip()], punit, cell, alat, nat)
    return cell, sym, frac


def read_output(text, mode="final", input_text=None):
    m = re.search(r"lattice parameter \(alat\)\s+=\s+([\d.]+)\s+a\.u\.", text)
    alat = float(m.group(1)) if m else None
    nat_m = re.search(r"number of atoms/cell\s+=\s+(\d+)", text)
    nat = int(nat_m.group(1)) if nat_m else None
    if mode == "final":
        if "Begin final coordinates" not in text:
            raise ValueError("no 'Begin final coordinates' block (relaxation not finished); use --evaluated")
        region = text.rsplit("Begin final coordinates", 1)[1].split("End final coordinates", 1)[0]
    else:
        last_bang = text.rfind("\n!")
        if last_bang < 0:
            raise ValueError("no '!' energy in output")
        region_all = text[:last_bang]
        k = region_all.rfind("ATOMIC_POSITIONS (")
        if k < 0:
            if input_text is None:
                raise ValueError("last '!' belongs to the starting geometry; pass --input")
            return read_input(input_text)
        c = region_all.rfind("CELL_PARAMETERS (", 0, k)
        prev_pos = region_all.rfind("ATOMIC_POSITIONS (", 0, k)
        start = c if c > prev_pos else k
        region = region_all[start:]
    lines = region.splitlines()
    cell = None
    for i, l in enumerate(lines):
        s = l.strip()
        if s.startswith("CELL_PARAMETERS"):
            mm = re.search(r"alat=\s*([\d.]+)", s)
            if mm:
                cell = _cell_block([x for x in lines[i + 1:] if x.strip()], "alat", float(mm.group(1)))
            else:
                unit = "bohr" if "bohr" in s else "angstrom"
                cell = _cell_block([x for x in lines[i + 1:] if x.strip()], unit, alat)
            break
    if cell is None:
        if input_text is None:
            raise ValueError("geometry block has no CELL_PARAMETERS (fixed-cell relax); pass --input for the cell")
        cell = read_input(input_text)[0]
    pi = next(i for i, l in enumerate(lines) if l.strip().startswith("ATOMIC_POSITIONS"))
    unit = re.search(r"\((\w+)", lines[pi]).group(1).lower()
    sym, frac = _positions([l for l in lines[pi + 1:] if l.strip()], unit, cell, alat, nat)
    return cell, sym, frac


def _images(cell, rmax):
    b = np.linalg.inv(cell).T  # rows: reciprocal vectors without 2π; plane spacing d_i = 1/|b_i|
    n = [int(math.ceil(rmax * np.linalg.norm(bi))) + 1 for bi in b]
    return np.array([[i, j, k] for i in range(-n[0], n[0] + 1) for j in range(-n[1], n[1] + 1)
                     for k in range(-n[2], n[2] + 1)])


def neighbours(cell, frac, centre, idx, rmax):
    """Vectors (Å) from atom `centre` to every image of atoms `idx` within rmax, sorted by length.
    Fractional coordinates are wrapped into [0, 1) first, so unwrapped inputs do not miss neighbours."""
    if not len(idx):
        return np.zeros((0, 3)), np.zeros(0, dtype=int), np.zeros(0)
    w = frac - np.floor(frac)
    sh = _images(cell, rmax)
    d = (w[idx][None, :, :] + sh[:, None, :] - w[centre]) @ cell
    d = d.reshape(-1, 3)
    lab = np.tile(np.array(idx), len(sh))
    r = np.linalg.norm(d, axis=1)
    keep = (r > 1e-6) & (r <= rmax)
    o = np.argsort(r[keep])
    return d[keep][o], lab[keep][o], r[keep][o]


def kmesh(cell, spacing):
    b = 2 * math.pi * np.linalg.inv(cell).T
    return [max(1, math.ceil(np.linalg.norm(bi) / spacing - 1e-9)) for bi in b]


def symmetry(cell, sym, frac):
    try:
        import spglib
    except ImportError:
        return None
    els = [element(s) for s in sym]
    num = [sorted(set(els)).index(e) + 1 for e in els]
    out = {}
    for tol in (1e-3, 1e-2, 1e-1):
        sg = spglib.get_spacegroup((cell, frac, num), symprec=tol)
        ops = spglib.get_symmetry((cell, frac, num), symprec=tol)
        out[tol] = (sg, len(ops["rotations"]) if ops else 0)
    return out


def analyse(cell, sym, frac, formula=None, shells=(), expect_shell=None, pair_angle=None, expect_label=None,
            cis_cut=135.0, bridges=(), kspacing=None, expect_sg=None, expect_nops=None, min_dist=0.6):
    rep, fails = [], []
    els = np.array([element(s) for s in sym])
    counts = {str(e): int((els == e).sum()) for e in sorted(set(els))}
    vol = abs(np.linalg.det(cell))
    a, b, c = (np.linalg.norm(v) for v in cell)
    ang = [math.degrees(math.acos(np.dot(cell[i], cell[j]) / np.linalg.norm(cell[i]) / np.linalg.norm(cell[j])))
           for i, j in ((1, 2), (0, 2), (0, 1))]
    rep.append(f"cell |a| {a:.5f} |b| {b:.5f} |c| {c:.5f} Å; angles {ang[0]:.3f} {ang[1]:.3f} {ang[2]:.3f}°; "
               f"V {vol:.4f} Å^3; atoms {len(sym)} {counts}")
    nfu = None
    if formula:
        f = parse_formula(formula)
        ratios = {e: counts.get(e, 0) / n for e, n in f.items()}
        extra = set(counts) - set(f)
        z = list(ratios.values())[0]
        ok = not extra and all(abs(r - z) < 1e-9 for r in ratios.values()) and abs(z - round(z)) < 1e-9 and z >= 1
        nfu = int(round(z)) if ok else None
        rep.append(f"formula {formula}: " + (f"PASS, {nfu} f.u., V/f.u. {vol / nfu:.4f} Å^3" if ok else
                                             f"FAIL (ratios {ratios}, extra species {sorted(extra)})"))
        if not ok:
            fails.append("formula")
    s = symmetry(cell, sym, frac)
    if s:
        rep.append("spglib: " + "; ".join(f"{t:g} Å {sg} ({n} ops)" for t, (sg, n) in s.items()))
        sg01, n01 = s[1e-2]
        symbol, number = sg01.split()[0], sg01.split()[-1].strip("()")
        if expect_sg and str(expect_sg) not in (symbol, number):   # exact: P4/m must not pass P4/mmm
            fails.append(f"space group {sg01} != {expect_sg} at 0.01 Å")
        if expect_nops and n01 != int(expect_nops):
            fails.append(f"{n01} symmetry operations != {expect_nops} at 0.01 Å")
    else:
        rep.append("spglib not installed: symmetry not checked")
        if expect_sg or expect_nops:
            fails.append("symmetry expected (--expect-sg/--expect-nops) but spglib is not installed")
    allidx = list(range(len(sym)))
    near = [r[0] for r in (neighbours(cell, frac, i, allidx, 6.0)[2] for i in allidx) if len(r)]
    dmin = min(near) if near else float("inf")
    rep.append(f"minimum interatomic distance {dmin:.4f} Å")
    if dmin < min_dist:
        fails.append(f"minimum distance {dmin:.3f} < {min_dist} Å")
    if (expect_label or expect_shell) and not shells:
        fails.append("--expect-label/--expect-shell given without --shell: nothing would be checked")
    if expect_label and not pair_angle:
        fails.append("--expect-label needs --pair-angle")
    for spec in shells:
        parts = spec.split(":")
        cen, ligs, n = parts[0], parts[1].split(","), int(parts[2])
        rmax = float(parts[3]) if len(parts) > 3 else 4.0
        lig_idx = [i for i, e in enumerate(els) if e in ligs]
        for ci in [i for i, e in enumerate(els) if e == cen]:
            v, lab, r = neighbours(cell, frac, ci, lig_idx, rmax)
            v, lab, r = v[:n], lab[:n], r[:n]
            comp = "".join(f"{l}{sum(els[lab] == l)}" for l in ligs)
            line = f"  {sym[ci]}{ci}: {comp} r {r.min():.3f}-{r.max():.3f} Å" if len(r) else f"  {sym[ci]}{ci}: none"
            if len(r) < n:
                fails.append(f"{sym[ci]}{ci}: only {len(r)} ligands within {rmax} Å")
            if expect_shell and comp != expect_shell:
                fails.append(f"{sym[ci]}{ci}: shell {comp} != {expect_shell}")
            if pair_angle:
                pv = v[els[lab] == pair_angle]
                if len(pv) == 2:
                    t = math.degrees(math.acos(np.clip(pv[0] @ pv[1] / np.linalg.norm(pv[0]) / np.linalg.norm(pv[1]),
                                                       -1, 1)))
                    label = "cis" if t < cis_cut else "trans"
                    line += f" {pair_angle}-{cen}-{pair_angle} {t:7.2f}° {label}"
                    if expect_label and label != expect_label:
                        fails.append(f"{sym[ci]}{ci}: {label} != expected {expect_label}")
                else:
                    line += f" ({len(pv)} {pair_angle} in shell)"
                    if expect_label:
                        fails.append(f"{sym[ci]}{ci}: {len(pv)} {pair_angle} in shell, cannot label")
            rep.append(line)
    for spec in bridges:
        A, X, B = spec.split(":")
        Ai = [i for i, e in enumerate(els) if e == A]
        Bi = [i for i, e in enumerate(els) if e == B]
        angs = []
        for xi in [i for i, e in enumerate(els) if e == X]:
            va = neighbours(cell, frac, xi, Ai, 5.0)[0]
            if A == B:   # same element at both ends: its two nearest distinct neighbours (images count)
                if len(va) < 2:
                    continue
                v1, v2 = va[0], va[1]
            else:
                vb = neighbours(cell, frac, xi, Bi, 5.0)[0]
                if not (len(va) and len(vb)):
                    continue
                v1, v2 = va[0], vb[0]
            angs.append(math.degrees(math.acos(np.clip(v1 @ v2 / np.linalg.norm(v1) / np.linalg.norm(v2), -1, 1))))
        if angs:
            rep.append(f"bridge {A}-{X}-{B}: min {min(angs):.2f} mean {np.mean(angs):.2f} max {max(angs):.2f}° "
                       f"({len(angs)} {X})")
    if kspacing:
        rep.append(f"k mesh for spacing {kspacing} 1/Å (2π included): {kmesh(cell, kspacing)} 0 0 0")
    rep.append("GATE PASS" if not fails else "GATE FAIL: " + "; ".join(fails))
    return not fails, "\n".join(rep), nfu


def write_cards(path, cell, sym, frac):
    with open(path, "w") as f:
        f.write("CELL_PARAMETERS angstrom\n")
        f.writelines("  " + " ".join(f"{x:.10f}" for x in v) + "\n" for v in cell)
        f.write("ATOMIC_POSITIONS crystal\n")
        f.writelines(f"  {s:<4} " + " ".join(f"{x:.10f}" for x in p) + "\n" for s, p in zip(sym, frac))


def selftest():
    """Cubic perovskite ABX3: B-X-B must be 180 deg, A-X-B 90 deg, formula and 6-fold B shell must pass."""
    cell = np.eye(3) * 3.989
    sym = ["K", "Ta", "O", "O", "O"]
    frac = np.array([[0, 0, 0], [.5, .5, .5], [.5, .5, 0], [.5, 0, .5], [0, .5, .5]], dtype=float)
    ok, rep, _ = analyse(cell, sym, frac, "KTaO3", ["Ta:O:6:2.5"], "O6", bridges=["Ta:O:Ta", "K:O:Ta"])
    got = {m.group(1): float(m.group(2)) for m in re.finditer(r"bridge (\S+): min ([\d.]+)", rep)}
    want = {"Ta-O-Ta": 180.0, "K-O-Ta": 90.0}
    bad = [k for k, v in want.items() if abs(got.get(k, -1) - v) > 0.01]
    if not ok or bad:
        print(rep)
        sys.exit(f"self-test FAILED: {bad or 'gate'}")
    print("self-test passed (bridges 180.00 and 90.00 deg, formula and shell gates)")


def main():
    if sys.argv[1:] == ["--check"]:
        if np is None:
            sys.exit("structure_gate.py needs numpy: python3 -m pip install numpy")
        selftest()
        return
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--final", action="store_true")
    g.add_argument("--evaluated", action="store_true")
    ap.add_argument("--input")
    ap.add_argument("--formula")
    ap.add_argument("--shell", action="append", default=[])
    ap.add_argument("--expect-shell")
    ap.add_argument("--pair-angle")
    ap.add_argument("--expect-label", choices=["cis", "trans"])
    ap.add_argument("--cis-cut", type=float, default=135.0)
    ap.add_argument("--bridge", action="append", default=[])
    ap.add_argument("--kspacing", type=float)
    ap.add_argument("--expect-sg")
    ap.add_argument("--expect-nops", type=int)
    ap.add_argument("--min-dist", type=float, default=0.6)
    ap.add_argument("--write-cards")
    a = ap.parse_args()
    if np is None:
        sys.exit("structure_gate.py needs numpy: python3 -m pip install numpy")
    text = open(a.file, errors="replace").read()
    inp = open(a.input, errors="replace").read() if a.input else None
    try:
        if a.final or a.evaluated:
            cell, sym, frac = read_output(text, "final" if a.final else "evaluated", inp)
            src = f"{a.file} ({'final coordinates' if a.final else 'last evaluated geometry'})"
        else:
            cell, sym, frac = read_input(text)
            src = a.file
    except (ValueError, StopIteration, AttributeError) as e:
        print(f"GATE FAIL: cannot read geometry from {a.file}: {e}")
        sys.exit(1)
    ok, rep, _ = analyse(cell, sym, frac, a.formula, a.shell, a.expect_shell, a.pair_angle, a.expect_label,
                         a.cis_cut, a.bridge, a.kspacing, a.expect_sg, a.expect_nops, a.min_dist)
    print(f"source: {src}\n```\n{rep}\n```")
    if a.write_cards:
        write_cards(a.write_cards, cell, sym, frac)
        print(f"cards written to {a.write_cards}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
