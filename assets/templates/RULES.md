# Hard rules ({{PROJECT}})

Read before every launch, kill or decision. Project-specific rules are added at the bottom with a REASONING-LOG ID.

| # | Rule |
|---|---|
| R1 | CITE-FIRST. No input value, no run, no decision without a cite (VERBATIM / SoT / METHOD / USER / QEDEF) recorded in the folder CITES.md and CITE-LOG.md. |
| R2 | CHAIN. cite START → input → structure gate → critic → launch → RUNBOOK line → result → sync → acceptance gates → critic → cite DONE → CLAIMS row. Every step leaves a file. |
| R3 | SECOND CHECK. Opus critique after every meaningful step; Codex too when installed. Saved in 12-critique/ before acting. Disagreement is resolved by evidence and both sides are logged. |
| R4 | VERIFY, DON'T TRUST. STATUS, handoffs, summaries and memory are claims; re-derive from raw outputs. DONE is not ACCEPTED. |
| R5 | NEVER INVENT PARAMETERS. Cutoffs, k, U, smearing, thresholds, strains, amplitudes, magnetic order: all cited. Numerical-only rescues (mixing) are cited METHOD with a critic verdict. |
| R6 | STRUCTURE GATE. Formula per f.u., coordination including periodic images, space group and symmetry count, before every launch and every follow-up (FORMULA-CHECK.md). |
| R7 | FAIR COMPARISON. Same Hamiltonian, matched k density, same structural freedom, per-f.u. normalisation, all endpoints stationary at final settings. |
| R8 | BOX EFFICIENCY. One rank per physical core, disjoint taskset slots, no idle cores >15 min without a logged reason, scratch cleaned, free disk <5 GB = hard stop. |
| R9 | SYNC. Mirror every ≤10 min; checksum dry-run with zero differences before any release; the box disk is not persistent. |
| R10 | PROCESS SAFETY. No pkill/pgrep -f over ssh; explicit PIDs only; restarts through uploaded scripts; no truncated dry runs. |
| R11 | HONEST FRAMING. Probes, bounds and unconverged values are labelled; failed gates stay on record; no claim beyond the evidence. |
| R12 | MONEY AND IRREVERSIBLE ACTIONS. Renting, extending, destroying boxes, deleting outputs, submitting or depositing need the user's go-ahead. |
| R13 | SECRETS. API keys and private keys never in any file, log, memory or remote box. |
| R14 | NO COMPUTE ON THE LAPTOP. Plan and check locally; compute runs on rented servers. |
| R15 | REAL CLOCK. Every log stamp comes from the clock at write time (logbook.py), never an estimate. |
