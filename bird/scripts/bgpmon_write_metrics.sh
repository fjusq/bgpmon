#!/usr/bin/env sh
# Writes minimal metrics JSON for SNMP (or anything) to consume.
# Depends on: birdc (and optionally birdc6)

set -eu

OUT="/var/run/bgpmon/metrics.json"
TMP="${OUT}.tmp"

mkdir -p "$(dirname "$OUT")"

get_v4() {
  # Try to read a total route count (best-effort)
  birdc -r -q 'show route count' 2>/dev/null \
    | awk '/Routes:/ {print $2; exit}' 2>/dev/null || echo 0
}

get_v6() {
  if command -v birdc6 >/dev/null 2>&1; then
    birdc6 -r -q 'show route count' 2>/dev/null \
      | awk '/Routes:/ {print $2; exit}' 2>/dev/null || echo 0
  elif [ -S /run/bird/bird6.ctl ]; then
    birdc -r -s /run/bird/bird6.ctl -q 'show route count' 2>/dev/null \
      | awk '/Routes:/ {print $2; exit}' 2>/dev/null || echo 0
  else
    echo 0
  fi
}

: "${METRICS_INTERVAL:=30}"  # seconds; override via env if you want

while :; do
  NOW="$(date +%s)"
  V4="$(get_v4 || echo 0)"
  V6="$(get_v6 || echo 0)"

  # write atomically
  {
    printf '{'
    printf '"updated_unix": %s, ' "$NOW"
    printf '"total_prefixes_v4": %s, ' "${V4:-0}"
    printf '"total_prefixes_v6": %s' "${V6:-0}"
    printf '}\n'
  } > "$TMP" && mv -f "$TMP" "$OUT"

  sleep "$METRICS_INTERVAL"
done
