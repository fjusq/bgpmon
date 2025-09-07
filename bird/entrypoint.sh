#!/usr/bin/env bash
set -euo pipefail

# Defaults (can be overridden by env)
: "${PEER_COUNT:=0}"
: "${BIRD_LOG_LEVEL:=all}"   # 'all' guarantees valid "log stderr all;" if template isn't using @@LOG_DIRECTIVE@@ yet
: "${BIRD_GR_TIMER:=240}"
: "${BIRD_SCAN_TIME:=15}"

TEMPLATE="/app/bird.conf.tmpl"
OUT="/etc/bird/bird.conf"

mkdir -p /etc/bird

# --- Build PEERS_SNIPPET from PEER_COUNT and PEER_i_* env vars ---
PEERS_SNIPPET=""
for i in $(seq 1 "${PEER_COUNT:-0}"); do
  name_var="PEER_${i}_NAME"
  addr_var="PEER_${i}_ADDR"
  asn_var="PEER_${i}_ASN"
  role_var="PEER_${i}_ROLE"
  md5_var="PEER_${i}_MD5"
  mh_var="PEER_${i}_MULTIHOP"
  src_var="PEER_${i}_SOURCE"
  ht_var="PEER_${i}_HOLDTIME"

  name="${!name_var:-}"
  addr="${!addr_var:-}"
  asn="${!asn_var:-}"
  role="${!role_var:-active}"
  md5="${!md5_var:-}"
  multihop="${!mh_var:-0}"
  source_addr="${!src_var:-}"
  holdtime="${!ht_var:-}"

  # Require name, address, and ASN
  if [ -z "$name" ] || [ -z "$addr" ] || [ -z "$asn" ]; then
    echo "WARN: Peer $i missing NAME/ADDR/ASN — skipping" >&2
    continue
  fi

  # Choose IPv4/IPv6 template
  if [[ "$addr" == *:* ]]; then
    fam="v6"; tpl="PEER_V6"
  else
    fam="v4"; tpl="PEER_V4"
  fi

  # Optional lines
  passive_line=""
  [[ "$role" == "passive" ]] && passive_line="  passive on;"

  pwd_line=""
  [[ -n "$md5" ]] && pwd_line="  password \"${md5}\";"

  mh_line=""
  if [[ -n "$multihop" && "$multihop" -gt 0 ]]; then
    mh_line="  multihop ${multihop};"
  fi

  src_line=""
  [[ -n "$source_addr" ]] && src_line="  source address ${source_addr};"

  ht_line=""
  [[ -n "$holdtime" ]] && ht_line="  hold time ${holdtime};"

  STANZA="$(
    cat <<EOF
# Peer ${i}: ${name}, (local AS${asn}, ${fam})
protocol bgp ${name}_${fam} from ${tpl} {
  neighbor ${addr} as ${asn};
  description "${name} ${fam}";
${pwd_line}
${mh_line}
${src_line}
${passive_line}
${ht_line}
}
EOF
  )"
  STANZA="$(printf '%s\n' "$STANZA" | sed '/^[[:space:]]*$/d')"

  if [ -z "$PEERS_SNIPPET" ]; then
    PEERS_SNIPPET="$STANZA"
  else
    PEERS_SNIPPET="${PEERS_SNIPPET}

${STANZA}"
  fi
done

# --- Valid BIRD log directive (brace style for non-'all' levels) ---
if [[ "${BIRD_LOG_LEVEL}" == "all" ]]; then
  LOG_DIRECTIVE='log stderr all;'
else
  LOG_DIRECTIVE="log stderr { ${BIRD_LOG_LEVEL} };"
fi

# --- Render from template (escape &, \ and convert newlines to \n for sed) ---
SNIP_ESCAPED=$(printf '%s' "$PEERS_SNIPPET" \
  | sed -e 's/[&\]/\\&/g' -e ':a;N;$!ba;s/\n/\\n/g')

sed \
  -e "s|@@ROUTER_ID@@|${ROUTER_ID}|g" \
  -e "s|@@LOCAL_AS@@|${LOCAL_AS}|g" \
  -e "s|@@BIRD_LOG_LEVEL@@|${BIRD_LOG_LEVEL}|g" \
  -e "s|@@LOG_DIRECTIVE@@|${LOG_DIRECTIVE}|g" \
  -e "s|@@BIRD_SCAN_TIME@@|${BIRD_SCAN_TIME}|g" \
  -e "s|@@PEERS_SNIPPET@@|$SNIP_ESCAPED|g" \
  "$TEMPLATE" > "$OUT"

# start metrics writer in background
/usr/local/bin/bgpmon_write_metrics.sh &

# --- Validate (non-fatal) & run bird in foreground ---
bird -p -c "$OUT" || echo "Config check FAILED — continuing so you can debug"
bird -f -d -c "$OUT" || {
  echo "BIRD exited with code $? — keeping container alive for debugging"
}
tail -f /dev/null
