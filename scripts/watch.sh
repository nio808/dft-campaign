#!/bin/bash
# Laptop-side watcher for ONE box (template; generalised from Project A's c067d_watch.sh). Every value in the configure
# block is a placeholder: set it per box and project. Every 10 min:
#   1. rsync the box queue into its OWN mirror folder (never into a folder you edit; box disks are not persistent)
#   2. run the status script on the box; NEW alert keys -> ALERTS.txt (tagged [BOX]) + one MASTER-RUNBOOK line
#      (persistent alerts are reported once, cleared alerts are noted once)
#   3. every 6th cycle: the full status block -> MASTER-RUNBOOK.md and STATUS-latest.txt
#   4. ssh failures counted; ALERTS + runbook only on the 1st and every 6th consecutive failure
# Read-only towards jobs. Single instance via pid file. Stop: touch "$MIRROR/WATCH-STOP" (do this when the box is
# released, or it keeps alerting into the runbook for days). Run (macOS): nohup caffeinate -i ./watch.sh > watch.stdout 2>&1 &   (Linux: nohup ./watch.sh ... or systemd-inhibit)
set -u
# ----------------------------------------------------------------------------- configure per box
BOX=boxD                                         # stable name, never reused
HOST=root@203.0.113.10                           # placeholder: user@host of the box
PORT=22
KEY=$HOME/.ssh/your_key_name                    # key NAME only in docs; never copy keys into the repo
REMOTE_Q=/workspace/runs/queue_main              # queue directory on the box
PROJECT=$HOME/projects/myproject                 # project root (holds MASTER-RUNBOOK.md)
MIRROR=$PROJECT/runs/40-campaign/queue_main      # local mirror of REMOTE_Q (this script may live here)
ALERTS=$PROJECT/runs/40-campaign/ALERTS.txt
REMOTE_PY=python3                                # python on the box that has numpy (e.g. /venv/main/bin/python)
STATUS_EXTRA=""                                  # optional, project-specific and cited, e.g.
                                                 #   "--atoms-per-fu 5 --ref X=<E_ref Ry per f.u.>"
STATUS_CMD="cd $REMOTE_Q && $REMOTE_PY qe_status.py */ --state state.json --scheduler qsched.py --schedlog sched.log $STATUS_EXTRA"
FOLDER_TAG=runs/40-campaign                      # folder name written into runbook lines
INTERVAL=600
TZ_NAME=""                                       # IANA zone for log stamps (same as the project's logbook);
TZ_LABEL=""                                      #   empty = machine local time, label = UTC offset
# -----------------------------------------------------------------------------
stamp() { if [ -n "$TZ_NAME" ]; then TZ=$TZ_NAME date '+%Y-%m-%d %H:%M'; else date '+%Y-%m-%d %H:%M'; fi; }
if [ -z "$TZ_LABEL" ]; then
  if [ -n "$TZ_NAME" ]; then TZ_LABEL=${TZ_NAME##*/}; else TZ_LABEL="UTC$(date +%z)"; fi
fi
SSH="ssh -i $KEY -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=30 -o ServerAliveInterval=30 \
-o LogLevel=ERROR -o StrictHostKeyChecking=accept-new -p $PORT"
RUNBOOK=$PROJECT/MASTER-RUNBOOK.md
PIDF=$MIRROR/.watch.pid
PREV=$MIRROR/.alerts.prev
mkdir -p "$MIRROR"
if [ -f "$PIDF" ] && kill -0 "$(cat "$PIDF")" 2>/dev/null; then
  echo "watcher for $BOX already running (pid $(cat "$PIDF")); exiting" >&2; exit 1
fi
echo $$ > "$PIDF"
trap 'rm -f "$PIDF"' EXIT
i=0; fails=0
while [ ! -f "$MIRROR/WATCH-STOP" ]; do
  ts=$(stamp)
  if rsync -a --timeout=120 -e "$SSH" --exclude 'qsched.py' --exclude 'qe_status.py' --exclude 'structure_gate.py' \
       --exclude 'watch*.sh' --exclude 'state.json.tmp' --exclude '.lock' --exclude 'tmp/' --exclude '*.save/' \
       --exclude '*.wfc*' "$HOST:$REMOTE_Q/" "$MIRROR/" 2>>"$MIRROR/watch.err"; then
    echo "$ts sync ok" >> "$MIRROR/watch.log"
  else
    echo "$ts SYNC FAIL" >> "$MIRROR/watch.log"
  fi
  if S=$($SSH "$HOST" "$STATUS_CMD" 2>>"$MIRROR/watch.err"); then
    fails=0
    printf '%s %s\n%s\n' "$ts" "$TZ_LABEL" "$S" > "$MIRROR/STATUS-latest.txt"
    A=$(printf '%s\n' "$S" | grep "ALERT")
    # De-duplicate: an alert is keyed by (job or source, ALERT type); only keys not present last cycle are reported,
    # so a persistent alert wakes the Monitor once instead of every 10 minutes. Cleared keys are logged once.
    KEYS=$(printf '%s\n' "$A" | awk '{n=$1; if (n ~ /^[0-9][0-9][0-9][0-9]-/) n="box";
             for (i=1;i<=NF;i++) if ($i ~ /^ALERT-/) {k=$i; sub(/\(.*$/, "", k); print n" "k}}' | sort -u | sed '/^$/d')
    NEW=$(comm -13 <(sort -u "$PREV" 2>/dev/null) <(printf '%s\n' "$KEYS" | sed '/^$/d'))
    GONE=$(comm -23 <(sort -u "$PREV" 2>/dev/null) <(printf '%s\n' "$KEYS" | sed '/^$/d'))
    printf '%s\n' "$KEYS" > "$PREV"
    if [ -n "$NEW" ]; then
      printf '%s %s [%s] NEW: %s\n%s\n' "$ts" "$TZ_LABEL" "$BOX" "$(printf '%s' "$NEW" | tr '\n' ';')" "$A" >> "$ALERTS"
      echo "- $ts $TZ_LABEL | ALERT | $FOLDER_TAG | [$BOX] new alert(s): $(printf '%s' "$NEW" | tr '\n' ';') see ALERTS.txt; no action taken | cites - | -" >> "$RUNBOOK"
    fi
    if [ -n "$GONE" ]; then
      echo "- $ts $TZ_LABEL | NOTE | $FOLDER_TAG | [$BOX] alert(s) cleared: $(printf '%s' "$GONE" | tr '\n' ';') | cites - | -" >> "$RUNBOOK"
    fi
    if [ $((i % 6)) -eq 0 ]; then
      { echo "- $ts $TZ_LABEL | CHECK | $FOLDER_TAG | [$BOX] hourly watcher status block (read-only): | cites - | -"
        echo '```'; echo "$S"; echo '```'; } >> "$RUNBOOK"
    fi
  else
    fails=$((fails + 1))
    if [ $fails -eq 1 ] || [ $((fails % 6)) -eq 0 ]; then   # rate-limited: 1st, then hourly
      echo "$ts $TZ_LABEL [$BOX] ALERT-SSH status query failed ($fails in a row)" >> "$ALERTS"
      echo "- $ts $TZ_LABEL | ALERT | $FOLDER_TAG | [$BOX] status query failed ($fails consecutive; see watch.err); if the box was released, touch WATCH-STOP | cites - | -" >> "$RUNBOOK"
    fi
  fi
  i=$((i + 1))
  sleep "$INTERVAL"
done
echo "$(stamp) watcher $BOX stopped by WATCH-STOP" >> "$MIRROR/watch.log"
