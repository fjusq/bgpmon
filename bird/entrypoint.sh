#!/usr/bin/env bash
set -euo pipefail

# ---- expected env (already in your compose .env) ----
: "${LOCAL_AS:?LOCAL_AS is required}"
: "${ROUTER_ID:?ROUTER_ID is required}"
: "${PEER_COUNT:=0}"

# tunables (have sane defaults)
: "${BIRD_SCAN_TIME:=15}"
: "${BIRD_LOG_LEVEL:=all}"
: "${BIRD_SOCKET_DIR:=/run/bird}"
: "${BIRD_CTL:=${BIRD_SOCKET_DIR}/bird.ctl}"
: "${BIRD_CONF:=/etc/bird/bird.conf}"
: "${BIRD_TEMPLATE:=/app/bird.conf.tmpl}"

# ensure paths exist
mkdir -p /etc/bird "${BIRD_SOCKET_DIR}"
chmod 777 "${BIRD_SOCKET_DIR}"

# ---- optional: render your config from a template ----
# If you keep your dynamic template, wire it here; otherwise remove this block.
if [[ -f "${BIRD_TEMPLATE}" ]]; then
  PEERS_SNIPPET=""
  for i in $(seq 1 "${PEER_COUNT}"); do
    name_var="PEER_${i}_NAME"; addr_var="PEER_${i}_ADDR"; asn_var="PEER_${i}_ASN"
    role_var="PEER_${i}_ROLE"; md5_var="PEER_${i}_MD5"; mh_var="PEER_${i}_MULTIHOP"
    src_var="PEER_${i}_SOURCE"; ht_var="PEER_${i}_HOLDTIME"

    name="${!name_var:-}"; addr="${!addr_var:-}"; asn="${!asn_var:-}"
    role="${!role_var:-active}"; md5="${!md5_var:-}"; multihop="${!mh_var:-0}"
    src="${!src_var:-}"; hold="${!ht_var:-}"

    [[ -z "$name" || -z "$addr" || -z "$asn" ]] && { echo "WARN: peer $i missing NAME/ADDR/ASN – skipping" >&2; continue; }

    [[ "$addr" == *:* ]] && base="PEER_V6" || base="PEER_V4"
    passive=""; [[ "$role" == "passive" ]] && passive=" passive on;"
    pwd=""; [[ -n "$md5" ]] && pwd=" password \"${md5}\";"
    mh="";  [[ "$multihop" =~ ^[0-9]+$ && "$multihop" -gt 0 ]] && mh=" multihop ${multihop};"
    src_line=""; [[ -n "$src" ]] && src_line=" source address ${src};"
    ht=""; [[ -n "$hold" ]] && ht=" hold time ${hold};"

    read -r -d '' STANZA <<EOF || true
protocol bgp ${name} from ${base} {
  neighbor ${addr} as ${asn};${passive}${pwd}${mh}${src_line}${ht}
}
EOF
    PEERS_SNIPPET+=$'\n'"${STANZA}"$'\n'
  done

  sed -e "s|@@ROUTER_ID@@|${ROUTER_ID}|g" \
      -e "s|@@LOCAL_AS@@|${LOCAL_AS}|g" \
      -e "s|@@BIRD_SCAN_TIME@@|${BIRD_SCAN_TIME}|g" \
      -e "s|@@PEERS_SNIPPET@@|${PEERS_SNIPPET//$'\n'/'\n'}|g" \
      "${BIRD_TEMPLATE}" > "${BIRD_CONF}"
fi

# prepend logging if your template/flat config didn't include it
grep -q '^log ' "${BIRD_CONF}" 2>/dev/null || sed -i "1s|^|log stderr ${BIRD_LOG_LEVEL};\n|" "${BIRD_CONF}"

echo "=== bird.conf ==="
sed -n '1,120p' "${BIRD_CONF}" || true
echo "================="

# nice to have: test the config; don't die if it fails
if ! bird -p -s "${BIRD_CTL}" -c "${BIRD_CONF}"; then
  echo "WARNING: bird -p reported errors; starting anyway for debugging" >&2
fi

# run BIRD in foreground with explicit control socket
exec bird -f -d -s "${BIRD_CTL}" -c "${BIRD_CONF}"
