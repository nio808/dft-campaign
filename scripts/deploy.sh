#!/bin/bash
# Copy reviewed files to a box and prove the box copies are byte-identical (SHA-256 both sides); write a manifest.
# usage: bash deploy.sh MANIFEST.json "ssh -i KEY -p PORT user@host" REMOTE_DIR FILE [FILE ...]
# Exit 1 on any hash mismatch. Record the manifest path in the folder RUNBOOK (logbook.py log ... FIX/LAUNCH).
# A sync loop must not overwrite these files afterwards: pause it while editing, verify hashes both ways after.
set -euo pipefail
if [ $# -lt 4 ] || [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  sed -n '2,5p' "$0" | sed 's/^# \{0,1\}//'; [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; exit $?
fi
MAN=$1; SSH=$2; RDIR=$3; shift 3
host=${SSH##* }; sshopts=${SSH% *}; sshopts=${sshopts#ssh}
port=$(printf '%s' "$sshopts" | sed -n 's/.*-p \([0-9]*\).*/\1/p'); key=$(printf '%s' "$sshopts" | sed -n 's/.*-i \([^ ]*\).*/\1/p')
scpopts=""; [ -n "$port" ] && scpopts="$scpopts -P $port"; [ -n "$key" ] && scpopts="$scpopts -i $key"
$SSH "mkdir -p '$RDIR'"
scp -q $scpopts "$@" "$host:$RDIR/"
fail=0; rows=""
for f in "$@"; do
  l=$(shasum -a 256 "$f" | cut -d' ' -f1)
  r=$($SSH "sha256sum '$RDIR/$(basename "$f")'" | cut -d' ' -f1)
  st=ok; [ "$l" = "$r" ] || { st=MISMATCH; fail=1; }
  echo "$st $(basename "$f") $l"
  rows="$rows{\"file\": \"$(basename "$f")\", \"sha256_local\": \"$l\", \"sha256_remote\": \"$r\", \"status\": \"$st\"},"
done
printf '{"utc": "%s", "remote": "%s:%s", "files": [%s]}\n' "$(date -u +%FT%TZ)" "$host" "$RDIR" "${rows%,}" > "$MAN"
echo "manifest $MAN"
exit $fail
