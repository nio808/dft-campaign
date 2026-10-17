#!/usr/bin/env python3
"""Lint Quantum ESPRESSO pw.x inputs before launch (pure Python, no dependencies).

usage: qe_lint.py INPUT.in [...] [--pseudo-dir DIR] [--cutoffs 60/480,80/640] [--expect key=value ...]
                  [--compare PARENT.in]

Checks (ERROR fails, WARN informs):
  ERROR duplicate key in a namelist (incl. indexed keys such as starting_magnetization(2))
  ERROR missing &CONTROL/&SYSTEM/&ELECTRONS; relax/md without &IONS; vc-relax/vc-md without &CELL
  ERROR nat != ATOMIC_POSITIONS lines; ntyp != ATOMIC_SPECIES lines; a species used but not declared
  ERROR nspin=2 without starting_magnetization or tot_magnetization
  ERROR K_POINTS card missing; pseudopotential file missing (when pseudo_dir is reachable or --pseudo-dir given)
  ERROR ecutwfc/ecutrho pair not in --cutoffs; --expect mismatch
  WARN  crystal_b/tpiba_b point weight 0 before the last point (QE 7.x generates no points for it)
  WARN  smearing without degauss; ecutrho < 4*ecutwfc; conv_thr / forc_conv_thr above --max-conv-thr /
        --max-forc-conv-thr (sanity heuristics only; the project's cited thresholds are what count)
  WARN  CR line endings; outdir on /dev/shm (create the parent before launch)
--compare prints every namelist key AND every physics card entry (ATOMIC_SPECIES mass + pseudopotential file, HUBBARD,
OCCUPATIONS, CONSTRAINTS, K_POINTS option and shift) that differs from PARENT.in, ignoring prefix/outdir/pseudo_dir and
the geometry cards; a different automatic k mesh is reported as INFO (meshes are recomputed per cell). This is how a
launch review shows "same physics as the cited parent"; it does not compare UPF file contents (hash them separately).
Exit 1 if any ERROR.
"""
import argparse
import os
import re
import sys

MECH = {"prefix", "outdir", "pseudo_dir", "wfcdir", "title", "verbosity"}


def strip_comments(text):
    out = []
    for line in text.splitlines():
        q = False
        for i, ch in enumerate(line):
            if ch in "'\"":
                q = not q
            if ch in "!#" and not q:
                line = line[:i]
                break
        out.append(line)
    return "\n".join(out)


def parse(text):
    """Return (namelists: {NAME: [(key, value, lineno)]}, cards: {CARD: (option, [lines])})."""
    body = strip_comments(text)
    lines = body.splitlines()
    nls, cards = {}, {}
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        if s.startswith("&"):
            name = s[1:].split()[0].upper()
            ent = nls.setdefault(name, [])
            i += 1
            while i < len(lines) and lines[i].strip() != "/":
                for m in re.finditer(r"([A-Za-z_][\w%]*(?:\([^)]*\))?)\s*=\s*('[^']*'|\"[^\"]*\"|[^,\s]+)", lines[i]):
                    ent.append((m.group(1).lower().replace(" ", ""), m.group(2).strip("'\""), i + 1))
                i += 1
        elif s and re.match(r"^[A-Z_]+\b", s) and s.split()[0] in (
                "ATOMIC_SPECIES", "ATOMIC_POSITIONS", "K_POINTS", "CELL_PARAMETERS", "HUBBARD", "OCCUPATIONS",
                "CONSTRAINTS", "ATOMIC_FORCES", "ADDITIONAL_K_POINTS", "ATOMIC_VELOCITIES", "SOLVENTS"):
            name = s.split()[0]
            opt = re.sub(r"[{}()]", " ", s[len(name):]).strip().lower()
            block = []
            i += 1
            while i < len(lines):
                t = lines[i].strip()
                if t.startswith("&") or (t and t.split()[0] in (
                        "ATOMIC_SPECIES", "ATOMIC_POSITIONS", "K_POINTS", "CELL_PARAMETERS", "HUBBARD", "OCCUPATIONS",
                        "CONSTRAINTS", "ATOMIC_FORCES", "ADDITIONAL_K_POINTS", "ATOMIC_VELOCITIES", "SOLVENTS")):
                    break
                if t:
                    block.append(t)
                i += 1
            cards[name] = (opt, block)
            continue
        i += 1
    return nls, cards


def flat(nls):
    d = {}
    for name, ent in nls.items():
        for k, v, _ in ent:
            d[(name, k)] = v
    return d


def num(v):
    try:
        return float(v.lower().replace("d", "e"))
    except (ValueError, AttributeError):
        return None


def lint(path, args):
    errs, warns = [], []
    raw = open(path, "rb").read()
    if b"\r" in raw:
        warns.append("CR (Windows) line endings; strip with tr -d '\\r'")
    text = raw.decode("utf-8", "replace")
    nls, cards = parse(text)
    for name, ent in nls.items():
        seen = {}
        for k, v, ln in ent:
            if k in seen:
                errs.append(f"&{name}: duplicate key '{k}' (lines {seen[k]} and {ln})")
            seen[k] = ln
    f = flat(nls)
    g = lambda k: next((v for (n, kk), v in f.items() if kk == k), None)
    for req in ("CONTROL", "SYSTEM", "ELECTRONS"):
        if req not in nls:
            errs.append(f"missing &{req}")
    calc = (g("calculation") or "scf").lower()
    if calc in ("relax", "md", "vc-relax", "vc-md") and "IONS" not in nls:
        errs.append(f"calculation='{calc}' needs &IONS")
    if calc in ("vc-relax", "vc-md") and "CELL" not in nls:
        errs.append(f"calculation='{calc}' needs &CELL")
    nat, ntyp = num(g("nat")), num(g("ntyp"))
    species = [l.split()[0] for l in cards.get("ATOMIC_SPECIES", ("", []))[1] if l.split()]
    pos = [l.split()[0] for l in cards.get("ATOMIC_POSITIONS", ("", []))[1] if l.split()]
    if nat is not None and pos and int(nat) != len(pos):
        errs.append(f"nat={int(nat)} but ATOMIC_POSITIONS has {len(pos)} lines")
    if ntyp is not None and species and int(ntyp) != len(species):
        errs.append(f"ntyp={int(ntyp)} but ATOMIC_SPECIES has {len(species)} lines")
    for s in sorted(set(pos) - set(species)):
        errs.append(f"species '{s}' in ATOMIC_POSITIONS not declared in ATOMIC_SPECIES")
    if num(g("nspin")) == 2 and not any(k.startswith("starting_magnetization") or k == "tot_magnetization"
                                        for (_, k) in f):
        errs.append("nspin=2 without starting_magnetization/tot_magnetization (QE starts non-magnetic)")
    occ = (g("occupations") or "").lower()
    if occ == "smearing" and g("degauss") is None:
        warns.append("occupations='smearing' without degauss (QE default 0)")
    ew, er = num(g("ecutwfc")), num(g("ecutrho"))
    if ew and er and er < 4 * ew - 1e-9:
        warns.append(f"ecutrho {er:g} < 4*ecutwfc {4 * ew:g}")
    if args.cutoffs and ew:
        allowed = {tuple(float(x) for x in p.split("/")) for p in args.cutoffs.split(",")}
        pair = (ew, er if er else 4 * ew)
        if not any(abs(pair[0] - a) < 1e-6 and abs(pair[1] - b) < 1e-6 for a, b in allowed):
            errs.append(f"cutoff pair {pair[0]:g}/{pair[1]:g} not in the documented set {args.cutoffs}")
    ct = num(g("conv_thr"))
    if ct is not None and ct > args.max_conv_thr:
        warns.append(f"conv_thr {ct:g} is loose for energies/forces")
    fct = num(g("forc_conv_thr"))
    if calc in ("relax", "vc-relax") and fct is not None and fct > args.max_forc_conv_thr:
        warns.append(f"forc_conv_thr {fct:g} Ry/bohr is loose")
    if "K_POINTS" not in cards:
        errs.append("no K_POINTS card")
    else:
        opt, blk = cards["K_POINTS"]
        if opt in ("crystal_b", "tpiba_b") and len(blk) > 2:
            for j, l in enumerate(blk[1:-1], start=1):
                parts = l.split()
                if len(parts) >= 4 and num(parts[3]) == 0:
                    warns.append(f"K_POINTS {opt}: point {j} has weight 0 (no points generated to the next vertex)")
        if opt == "automatic" and blk:
            m = blk[0].split()
            if len(m) != 6:
                errs.append(f"K_POINTS automatic line needs 6 integers, got '{blk[0]}'")
    od = g("outdir") or ""
    if od.startswith("/dev/shm"):
        warns.append(f"outdir {od}: create its parent directory before launch (QE does not)")
    pdir = args.pseudo_dir or g("pseudo_dir")
    if pdir:
        pdir = os.path.join(os.path.dirname(os.path.abspath(path)), pdir) if not os.path.isabs(pdir) else pdir
        if os.path.isdir(pdir):
            for l in cards.get("ATOMIC_SPECIES", ("", []))[1]:
                parts = l.split()
                if len(parts) >= 3 and not os.path.isfile(os.path.join(pdir, parts[2])):
                    errs.append(f"pseudopotential {parts[2]} not found in {pdir}")
        else:
            warns.append(f"pseudo_dir {pdir} not reachable here; pseudo files not checked (check on the box)")
    for e in args.expect or []:
        k, _, v = e.partition("=")
        got = g(k.strip().lower())
        if got is None or (num(got) is not None and num(v) is not None and abs(num(got) - num(v)) > 1e-12) or \
                (num(got) is None and got.lower() != v.strip().strip("'\"").lower()):
            errs.append(f"--expect {k}={v}: input has {got}")
    return errs, warns, f


def card_signature(cards):
    """Physics-relevant card content: species (mass, UPF), HUBBARD, OCCUPATIONS, CONSTRAINTS, K_POINTS option/mesh."""
    sig = {}
    for l in cards.get("ATOMIC_SPECIES", ("", []))[1]:
        p = l.split()
        if len(p) >= 3:
            sig[("ATOMIC_SPECIES", p[0])] = f"mass {p[1]} pseudo {p[2]}"
    for name in ("HUBBARD", "OCCUPATIONS", "CONSTRAINTS"):
        if name in cards:
            opt, blk = cards[name]
            sig[(name, "content")] = (opt + " | " + " ; ".join(" ".join(l.split()) for l in blk)).strip()
    if "K_POINTS" in cards:
        opt, blk = cards["K_POINTS"]
        sig[("K_POINTS", "option")] = opt or "tpiba"
        if opt == "automatic" and blk:
            m = blk[0].split()
            sig[("K_POINTS", "mesh")] = " ".join(m[:3])
            sig[("K_POINTS", "shift")] = " ".join(m[3:6])
        else:
            sig[("K_POINTS", "points")] = f"{len(blk)} lines"
    return sig


def compare(child_path, parent_path):
    """Every namelist key and physics card that differs from the parent. K_POINTS mesh differences are INFO: the
    mesh is recomputed per cell from the spacing rule, so a different mesh is expected for a different cell."""
    out = []
    cn, cc = parse(open(child_path, encoding="utf-8", errors="replace").read())
    pn, pc = parse(open(parent_path, encoding="utf-8", errors="replace").read())
    cf, pf = flat(cn), flat(pn)
    for key in sorted(set(cf) | set(pf)):
        if key[1] in MECH:
            continue
        a, b = pf.get(key), cf.get(key)
        if a is None or b is None or (num(a) is not None and num(b) is not None and abs(num(a) - num(b)) > 1e-12) or \
                (num(a) is None and str(a).lower() != str(b).lower()):
            out.append(("DIFF", f"&{key[0]} {key[1]}: parent={a} child={b}"))
    cs, ps = card_signature(cc), card_signature(pc)
    for key in sorted(set(cs) | set(ps)):
        a, b = ps.get(key), cs.get(key)
        if a != b:
            kind = "INFO" if key == ("K_POINTS", "mesh") else "DIFF"
            out.append((kind, f"{key[0]} {key[1]}: parent={a} child={b}"))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("--pseudo-dir")
    ap.add_argument("--cutoffs", help="allowed ecutwfc/ecutrho pairs, e.g. 60/480,80/640")
    ap.add_argument("--expect", nargs="*", help="key=value assertions, e.g. degauss=0.01 nspin=2")
    ap.add_argument("--compare", help="parent input whose physics must match")
    ap.add_argument("--max-conv-thr", type=float, default=1e-6, help="WARN above this conv_thr (lint heuristic)")
    ap.add_argument("--max-forc-conv-thr", type=float, default=1e-3,
                    help="WARN above this forc_conv_thr for relaxations (lint heuristic)")
    a = ap.parse_args()
    bad = 0
    for p in a.inputs:
        errs, warns, f = lint(p, a)
        status = "FAIL" if errs else "ok"
        print(f"{status:4s} {p}")
        for e in errs:
            print(f"  ERROR {e}")
        for w in warns:
            print(f"  WARN  {w}")
        if a.compare:
            d = compare(p, a.compare)
            nd = sum(1 for k, _ in d if k == "DIFF")
            print(f"  compare vs {a.compare}: " + ("identical physics (namelists, species/pseudos, HUBBARD, "
                                                   "OCCUPATIONS, CONSTRAINTS, K_POINTS option/shift)" if not nd
                                                   else f"{nd} physics difference(s)"))
            for k, x in d:
                print(f"  {k:4s} {x}")
        bad |= bool(errs)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
