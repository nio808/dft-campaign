# Verification gates: how each element, structure and property was checked

Contents: 1 Pseudopotentials, element by element · 2 Structure · 3 Convergence ladders · 4 Relaxation acceptance · 5 Reference state and volume · 6 Comparing candidate structures · 7 Electronic: bands, DOS/PDOS, HSE, effective masses · 8 Elastic constants · 9 Phonons · 10 EOS and pressure series · 11 Optics (Yambo) · 12 Formation and reaction energies · 13 Parsers and gate code · 14 Acceptance vocabulary

Each gate is written into the step README **before** the step runs. A result is "accepted" only when its gates pass and an independent post-result review agrees. A failing gate stays on record as a failure.

---

## 1. Pseudopotentials, element by element

Keep one `pseudo/README.md` (or `justify.txt`) with a table row per element. Project M's is the model. For each element check:

| Check | How | Why it mattered |
|---|---|---|
| Source and version | Table name and release (e.g. PseudoDojo NC SR v0.4.1, standard column), URL, download date | The table version (0.4.1) and the generator version printed in the file (ONCVPSP 3.3.0) are different numbers. Manuscripts mix them up. |
| Which entry | The table's own name for the file (e.g. an `-sp` semicore variant, a `-d` variant) and whether it is the standard or stringent choice | A reviewer asks "why not stringent?" Give the documented reason (e.g. a `-d` entry keeps the 3d in valence, as the table recommends). |
| Header | UPF version, `pseudo_type` (NC/US/PAW), `is_ultrasoft`, `is_paw`, `has_so`, functional, `core_correction` | Yambo and `epsilon.x` need NC. A completed PAW/US pass had to be discarded. NLCC flags matter for later caveats (HSE with NLCC). |
| Valence | Reference configuration, `z_valence`, then electrons per cell and occupied bands (2n valence electrons → n occupied bands) | Band-index gates (CBM = band n + 1) depend on it. Count from the UPF, never by hand. |
| Ghost states | The paper's ghost table or the DojoReport `ghosts` key | A two-electron alkaline-earth NC potential had a ghost about 80 eV up, which spoils empty states and optics; its semicore (s+p) variant removes it. Check before any empty-band work. |
| Cutoff hints | Low/normal/high from the DojoReport, **in hartree** (1 Ha = 2 Ry) | Hints set the ladder range, not the production cutoff. |
| Identity across trees and hosts | md5 printed by pw.x plus SHA-256 of the files; shared elements identical in both compounds | Same Hamiltonian for compared compounds. Box-side hashes must match before production. |
| Provenance hashing | Hash the UPFs into every input's cache key (`inhash` = input + DEPS + UPFs) | An in-place UPF replacement must invalidate cached results. |
| Mixed families | Allowed when disclosed (Project A: GBRV for some elements, PSLibrary for the rest, as SSSP ships them) with exact hashes | Not an error in itself. Changing libraries mid-paper is. |
| Projection orbitals | Does the UPF carry pseudo-atomic orbitals for every channel you want in a PDOS? | One semicore NC potential had l=2 projectors but no d pseudo-atomic orbital, so projwfc had no d PDOS channel for that element. State it. |

### Two verification routes that were actually used

**Route A: a curated library with a machine-readable manifest (Project A: SSSP 1.3.0 PBE Efficiency).**
1. Download the archive and its JSON from the Materials Cloud record. Check the md5 of both against the values the record publishes, and write the record URL and md5s into the cite file (Project A: `02-citations/C008-phase0-sssp-<elements>.md`).
2. For each element, read the file name, library of origin (GBRV, PSLibrary, ...), and recommended `cutoff_wfc`/`cutoff_rho` from the JSON. Check that the file's md5 matches the JSON entry (`match_json=True`).
3. Starting cutoff = the **maximum over all elements** of the recommended values. Project A: one light element drove 60/480 Ry. That number is a starting point; the project's own ladder (§3) decides.
4. A curated set mixes US and PAW. Use the set as published; no ad-hoc swaps of single elements. Record the hashes on every host (Project A: `C008-sssp-pp-sha256-<host>.md`) and in the paper's data (`pseudopotentials.json`).
5. Check property-code compatibility before choosing this route: Yambo/epsilon.x need NC, which a mixed US/PAW set cannot provide.

**Route B: a table of individually tested potentials (Project M: PseudoDojo NC SR v0.4.1, standard column).**
1. For each element, take the table's named entry and record why that entry. Examples: a semicore `-sp` entry removes the 80 eV ghost of a two-electron potential; a `-d` entry keeps 3d in valence, as recommended.
2. Read the UPF header yourself: type, functional, z_valence, NLCC, has_so. Read the DojoReport hints (hartree) and the ghost test.
3. Record md5 as printed by pw.x, and show identical files across compounds (the elements shared by the two compounds).
4. Write one row per element in `pseudo/README.md` (template from `logbook.py init`).

Whichever route: the per-element table, the hashes on every host and the electron count are recorded before any production input exists, and the Phase 1 critic checks them.

## 2. Structure

1. **Transcription.** Lattice constants, setting, Wyckoff sites and reported bond lengths against the experimental paper. Put the DOI in the README.
2. **Space group from the sites.** Read the Wyckoff sites, not only the printed symbol: a site set can exist only in the centrosymmetric group, and text extraction drops overbars ("I-42d" → "I42d", "Fm-3m" → "Fm3m", "R-3m" → "R33m"). Then confirm with QE's operation count (e.g. point group 4/mmm gives 16 operations, -3 gives 6) and with spglib at 0.01 Å.
3. **Formula per formula unit.** Count species per f.u. for every input (`scripts/structure_gate.py --formula`). Project A's gate required the exact anion counts per f.u.; a whole lineage with two anion counts swapped existed and is quarantined.
4. **Coordination with periodic images.** Build the nearest-neighbour shell of each centre from the 27 neighbouring cells. Project A checked that each octahedral centre had the expected 4 + 2 anion split among its six nearest neighbours, labelled the ordering from the angle between the two minority anions (adjacent < 135° < opposite), and required a maximum distance below a cited bound. Labels must match the parent's label.
5. **Primitive cell and vectors.** Write the transformation (e.g. obverse rhombohedral v1 = (2A+B+C)/3 ...). Check that the vectors give back a and c, and that the 3-fold axis lies along Cartesian z (optics axes and C14/C15 signs depend on it).
6. **Deposited CIF.** Read it if one exists (CSD deposits). Not reading it became a reviewer complaint ("unverified experimental geometry"). Compare bonds and angles with the experiment, not just lattice constants.
7. **ML seeds.** MACE/CHGNet pre-relaxed structures are internal seeds only, not reportable. They are usually rattled, so symmetrise before QE when the symmetry is real, or QE finds no symmetry and runs many more k-points and degrees of freedom.

Write the output to `FORMULA-CHECK.md` in the job folder: space group, V per f.u., per-centre shells, mesh, and `GATE PASS/FAIL`.

## 3. Convergence ladders

- Ladder on the experimental or start cell, varying **one** parameter: wavefunction cutoff at a generous fixed density cutoff, then the density dual, then the k mesh N = 2 … 12 (unshifted MP containing Γ), and smearing width for metals.
- **Rule** (declare the tolerances per project with `logbook.py gate`, apply them with `scripts/conv_ladder.py`). Project M kept the first value whose energy is within 1 meV/atom **and** whose pressure is within 1 kbar of the tightest point, with every tighter point also passing. Choose tolerances against the size of the effect the paper reports: a 6 meV/f.u. ordering needs tighter error bars than a 100 meV one. Read pressure from the stress tensor in Ry/bohr³ (×147105.079 kbar), not from the printed P with its 0.01 kbar resolution. A "tie" at print resolution caused a rule change in Project M.
- A failing lower cutoff does not cancel a plateau above it (80 Ry failed on pressure, 90 Ry kept).
- A mesh floor chosen after seeing the data ("4 = max(rule 2, floor 4)") is fine, but **say it was post hoc**.
- For energy differences between structures, test the **decisive pair** at fixed geometry with each parameter (e80: 80/640 Ry; k15: 0.15 Å⁻¹; d005: degauss 0.005 Ry), and report the **pair shift** (the change in E(I) − E(II)). In Project A the decisive pair's shifts were below 1 meV/f.u. against a margin of tens.
- Elastic constants, phonons and optics have their own convergence (§8–§11). Ground-state convergence does not carry over to them.
- Spin: if the system might be magnetic, compare NM and SP on matched controls, and check the final |M|. Spin-polarising a non-magnetic 40-atom cell doubled the cost and made the SCF wander.

## 4. Relaxation acceptance

A relaxation endpoint is accepted when all of these hold:
- `bfgs converged`, an `End final coordinates` block, and a final SCF with fresh G-vectors;
- in the **final** SCF, the largest Cartesian force component is below `forc_conv_thr` (1e-4 Ry/bohr in Projects A and M), stress is below `press_conv_thr` (0.5 kbar), and the SCF force correction is small compared with the total force;
- the symmetry operation count is unchanged and the structure gate passes on the final coordinates;
- it is **stationary at the final settings**. If the static uses a denser k mesh than the relaxation, check the forces in that static. Project A's closest competitor had a maximum component about 13× the threshold in its static, so its few-meV margin needed a fine-grid relaxation (which moved it by about 0.1 meV/f.u.);
- for soft frameworks, two starts reach the same minimum (Project M rotation check: ΔE below 1e-6 Ry, Δa 0.07%);
- a force/stress gate on the static, its high-cutoff copy and its dense-mesh copy (`scripts/fcheck.py`, e.g. max |F| < 1e-4, max |σ| < 0.5 kbar, cross differences < 1e-4 / 0.5).

Lineage to match published endpoints: coarse relaxation (0.3 Å⁻¹) → fine relaxation (0.2 Å⁻¹) → static (0.2 Å⁻¹). Tests run at the static geometry.

Unfinished relaxations: "Further relaxation can only lower E" makes an unrelaxed energy an **upper bound** on the relaxed energy at the same settings. That is useful for a bounded argument, never a reported endpoint.

## 5. Reference state and volume

Run this early, right after the first relaxation (cheap for small cells):

| Quantity | PBE | PBEsol | PBE-D3(BJ) | Experiment |
|---|---|---|---|---|
| V (Å³), error % | | | | |
| a, c, c/a | | | | |
| key bond lengths | | | | |
| key bridge or tilt angles | | | | |

- Compare against the **measured** structure: read the deposited CIF for bond lengths and bridge angles. Project M compared against a constructed anion site (regular polyhedra at the reported bond length), so its "experimental" bridge angles were not measurements.
- Split the volume error into a bond part (`structure_gate.py --shell` lengths) and an angle part (`--bridge` angles; law of cosines on the two centres). In Project M the three functionals gave nearly identical bonds (within ~0.01 Å), and the volumes differed through a bridge angle that moved by about 15° across them, so the error sat in the rotation.
- Decision rule (declare it): if |ΔV| ≤ about 3% and the shape ordering is right, use PBE. Otherwise either adopt the functional that gets the structure (and re-run convergence for it), or plan every headline property at **two** reference states (calculated and experimental volume), budgeted up front.
- Experimental-volume cells: iterate a hydrostatic pressure P* until V matches experiment within 0.1% (Project M: P* of about 1 GPa, V within 0.06%). The shape (a, c) stays the PBE shape at P* (a too short, c too long, by ~1–2%). Say so. Elastic constants at P* are Birch coefficients B_ij (σ₀ = −P*·I), not zero-pressure C_ij.

## 6. Comparing candidate structures

Before ranking energies, check:
- same code build, functional, pseudopotentials, cutoffs, smearing, spin treatment, U;
- matched k density (the same spacing rule), and the supercell-versus-cell mesh offset measured (about 1.4 meV/f.u. for one composition in Project A) and corrected;
- energies per formula unit, with atoms per f.u. counted from the actual cell;
- **the same structural freedom on both sides**: tilts, supercell size and symmetry constraints. Constrained (symmetry-kept) relaxations of some candidates and unconstrained ones of others bias a census (Project Y: 19 of 22 with symmetry);
- the final magnetic state of each (a spurious final-SCF moment once moved an energy by 90 meV);
- both endpoints relaxed at the final settings (§4).

## 7. Electronic structure

**Bands**
- Path from Setyawan–Curtarolo for the lattice type. Choose the variant by the actual angle (RHL1 for α < 90°) and compute η and ν from the relaxed cell (η = (1 + 4 cos α)/(2 + 4 cos α), ν = 3/4 − η/2).
- `K_POINTS crystal_b`: the integer is the number of points to the next vertex. **Weight 0 generates no points** in QE 7.x, so put 1 on a break point. A reviewer caught that before launch.
- `nosym=.true., noinv=.true.` so the path is not replaced by images. Read the density from the tight SCF.
- "eigenvalues not converged" warnings must be zero for a published plot. Rerun with `diago_full_acc=.true.` and more bands (Project A bands: from 1 warning to 0).
- Quote "PBE Kohn–Sham gap along the sampled path, direct at Γ". It is not an optical or quasiparticle gap. Check the path gap against the uniform-mesh gap; they must agree, and record both. A nearly flat top band weakens a "direct gap" claim.

**DOS / PDOS**
- NSCF on a uniform mesh. Tetrahedra for total DOS; Gaussian width tested.
- Gates: the DOS integral equals the electron count (QE weights add to 2 for non-spin, so a filled band integrates to 2). PDOS sum against total, with spilling reported. Mesh-pair L1 differences declared per width (Project M target 10³ → 12³ ≤ 5% at every width). A coarser mesh pair that genuinely failed at the narrowest width stays reported.
- `projwfc.x` can die in `d_matrix` ("D_S (l=3) ... not orthogonal") under rhombohedral symmetry. Use an NSCF with `nosym` (time reversal only), or `lsym=.false.` with `kresolveddos`.
- A full-range DOS written on a coarse grid undersamples semicore spikes. Plot the window that is converged, e.g. VBM + 20 eV.

**HSE06**
- Report it as the Γ (or sampled-mesh) gap. State nqx, ecutfock and `exxdiv_treatment`. Check that the band edge lies on the sampled mesh, and run a q-mesh check. Changing NK for memory must not change the physics.

**Effective masses**
- Electron masses from a fit around the CBM (band index from the electron count), with units converted from tpiba. Skip hole masses when the VBM is degenerate, and say why.

## 8. Elastic constants

- Know the Laue class: trigonal -3 has **seven** independent C_ij (C11, C12, C13, C14, C15, C33, C44), with C66 = (C11 − C12)/2, C24 = −C14, C25 = −C15. Signs depend on the Cartesian setting.
- Strains: linear, A' = A(I + ε)ᵀ, amplitudes ±0.25% and ±0.5%, ions relaxed in each strained cell (relaxed-ion constants), crystal coordinates starting from the relaxed values. Each case passes only if BFGS converges with max force < 1e-4 Ry/bohr.
- **Linearity test first** (seven fixed-cell relaxations at 0 and ±h). The slope gate was "passes within 80 kbar or 10%". Halve the strain only for a larger discrepancy after a converged relaxation.
- Fit: Project M's production used a quadratic fit over a 25-run design (the cubic amplified noise 3×). Acceptance: reciprocity and symmetry residual ≤ 0.5 GPa; B_H and G_H full range over the production, cubic, 6³ and 120 Ry variants ≤ 2%; Born criteria (Mouhat–Coudert 2014 for the class) **and** positive eigenvalues of the raw and projected tensors; minimum eigenvalue > 3u. Report endpoint "u" as a conditional allowance, not an uncertainty.
- Consistency: B_Reuss should agree with the EOS B0 (Project M: within 1% for both compounds). Compare with Reuss, not Hill.
- A 1 kbar stress error on a 1% strain is about 10 GPa in a modulus, so a relaxed but unstrained force check is a weak gate for elasticity.
- Before claiming a mechanism for an elastic anomaly, check what the saved stresses already show. The pre-relaxation stresses give clamped-ion constants; in Project M comparing them with the relaxed-ion constants settled the mechanism without new compute.
- Spin: elastic constants from NM runs when the energy ordering came from SP runs is a treatment difference. Disclose it, and check same-geometry NM/SP controls.

## 9. Phonons

- DFPT on the final cell, with the SCF at the same settings. `tr2_ph` tight. `epsil`/`zeu` for polar materials (Born charges, ε∞, non-analytic term).
- **ASR choice matters.** q2r `zasr='crystal'` against matdyn `asr='simple'` moved a direct grid mode by about 5 cm⁻¹. The raw Γ acoustic modes sat near 24 cm⁻¹. Compare the ASR variants at grid q, Γ and X before adopting one, and keep the result on HOLD until that is resolved.
- Wording follows the evidence. "Positive frequencies on the sampled 4³ grid; positive Γ optical modes after ASR" is defensible. "Dynamically stable" needs the full interpolated dispersion clean. **Report interpolated negative modes plainly** (Project M: one grid dipped to about −60 cm⁻¹); omitting them is an over-claim.
- Frozen-phonon checks: make the supercell match the q-vector. In Project Y a supercell doubled a and b instead of b and c, so the "stable" claim had to be retracted. Use a basis-checked ± displacement pair.
- Low-temperature thermodynamic rows (< 50 K) are not converged on coarse grids. Report the ZPE when you report thermodynamics.
- A q-point computed on another host is merged only after an overlap gate (same q on both hosts agrees within the declared 0.1 cm⁻¹; observed 0.002–0.006 cm⁻¹) and an identical-Hamiltonian check.

## 10. EOS and pressure series

- BM3 E(V) over about 0.94–1.06 V0 with nine volumes, using fixed-volume `cell_dofree='shape'` relaxations. Report V0, B0 and B0'. B0' from a narrow window is weak: an extrapolation to V/V0 = 0.80 missed the directly computed pressure badly. That is a window effect, so do not combine EOS and pressure fits.
- Cutoff check on the EOS (90 vs 120 Ry on the same five volumes, with a same-volume assertion).
- Pressure series: choose ranges that give a similar volume reduction (Project M: 0–10 GPa for the stiffer compound, 0–5 GPa for the softer, about 20% each) and say why. Gaps under pressure are mesh gaps; note where the VBM leaves Γ.
- Geometry bookkeeping: bind each pressure point's geometry to its output, and check the hash.

## 11. Optics (Yambo)

- Format gate: `p2y` on a small NSCF; the Yambo setup must report the same electrons, bands, k-points, symmetries, cell volume and gap as QE.
- Smoke gate: an IP spectrum ends with "Game Over" and reports `[r,Vnl] included : yes` (non-local commutator).
- **Band coverage gate**: the highest band must lie at least the spectral window (e.g. 30 eV) above the VBM at every k. Do not end the band range inside a degenerate pair (Yambo warns, e.g. 96/97 at one k): use a warning-free boundary.
- k and band convergence on integrated Im ε, peak position and ε₁(0), with declared tolerances (e.g. integral ≤ 2%, ε₁(0) ≤ 0.5%).
- Use **retarded** response (`GrFnTpXd='R'`). Time-ordered with η = 0.1 eV gives spurious sub-gap absorption (about 1000 cm⁻¹ at 3 eV). A Kramers–Kronig over a 0–30 eV window misses ε₁(0), so take it from the full response.
- A scissor to the HSE gap must be applied inside the response and labelled as such. Validators must read the corrected `[X+QP]` gap, not the bare `[X]`; a parser bug failed a correct run.
- Word it as "PBE independent-particle spectra, excluding local-field corrections". RPA ladders not converged in cutoff go to the SI, labelled, or are left out.
- Run optics on the final cell. If an earlier cell was used, the reviewer will ask, so justify it or rerun.

## 12. Formation and reaction energies

- Name the exact channel (e.g. a binary solid plus a molecular gas), the reference states, and that it is static 0 K. It is not a convex hull and not a finite-temperature stability proof.
- Molecules: a box size check (|E12 − E10| tiny), the spin state (O₂ triplet, total magnetisation 2.00), and the same pseudopotentials and cutoffs.
- Normalise per H₂ or per f.u. explicitly, and never mix per-cell and per-f.u. quantities (a per-cell cost was once compared against a per-f.u. RT).

## 13. Parsers and gate code

- Test every parser on real outputs of the exact code version before trusting it. Grep the output format the parser depends on.
- Use the **last** force block and the last stress tensor. Require every atom index exactly once and finite values. Reject NaN/inf explicitly, because `max()` over a list with NaN can pass.
- Use raw `!` lines for energies. Use the tensor for pressure. Check the band index against the electron count.
- Each gate script has a `--check` self-test: it passes a known-good output and fails a known-bad one (missing atom line, NaN, tighter bound).
- Cache keys: hash the input plus upstream dependencies (DEPS: the SCF whose density a bands run copies) plus the UPFs. Remove the old stamp before rerunning, so a failed rerun cannot inherit a good stamp. `set -u` with an unset DEPS once crashed a check mid-run, so use `${DEPS:-}`.
- Skip logic reruns unless the output is good **and** was produced from this exact input.

## 14. Acceptance vocabulary

Use these words consistently in READMEs and RUNLOG:
- **DONE**: execution finished.
- **PASS/FAIL**: a declared gate.
- **ACCEPTED**: gates passed and the post-review said GO.
- **HOLD**: evidence incomplete or contradictory; not usable in claims.
- **PROBE**: deliberately bounded or unconverged; reported as such.
- **STOPPED(reason)**: deliberately ended.
- **SUPERSEDED**: replaced, kept for the record.
- **QUARANTINED**: wrong identity; never enters tables.
