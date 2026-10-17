# Handoff ({{PROJECT}})

Updated {{NOW}} {{TZ}}. Details: MASTER-RUNBOOK.md (tail), STATUS.md, REASONING-LOG.md.

## Why this campaign exists (3–5 lines, with the numbers)

## Boxes (disks are NOT persistent: sync before destroying)
| Box | ssh (`-i <key name>`) | Cores | Queue dir | Status | $/h | Release when |
|---|---|---|---|---|---|---|

## Jobs (state at handoff)

## Results so far (synced, with paths)

## How to check
```
ssh -i ~/.ssh/<key> -p <port> <user>@<host> "cd <queue> && <python> qe_status.py <jobs> && tail -8 sched.log"
```

## Operating rules
- Pause new launches: `touch <queue>/STOP` (running jobs continue). Remove it to resume.
- Never pattern-kill over ssh; explicit PIDs only; restart the scheduler only via an uploaded script.
- Never rsync a box into the working tree; mirrors only.

## Monitors (which die with this session or machine)
- Laptop watcher(s): <script>, stop with WATCH-STOP.
- Agent hourly check and alert watch: session-only unless run by a system scheduler.

## Pick-up checklist on a new machine
1. Copy the ssh key securely (never via git). Regenerate any key that was pasted in chat.
2. `git pull`.
3. Decide who syncs (keep the old watcher or start a new one; never both).
4. New session: "Read HANDOFF.md and the tail of MASTER-RUNBOOK.md, check the boxes, re-create the hourly check and alert monitor."
5. When jobs finish: final rsync, checksum dry-run = 0 differences, stop watcher, user destroys box.

## Plan and pre-registered decision rule (exact wording per outcome)
