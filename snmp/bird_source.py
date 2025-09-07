# snmp/bird_source.py
import os, subprocess, re, ipaddress, logging, json
log = logging.getLogger("bgpmon.bird")

BIRD_SOCK = os.getenv("BIRD_SOCK", "/run/bird/bird.ctl")
BIRD_CMD  = ["birdc"] + (["-s", BIRD_SOCK] if BIRD_SOCK else [])

def _run(cmd):
    out = subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT)
    log.debug("CMD ok: %s", " ".join(cmd))
    log.debug("OUT head:\n%s", out[:800])
    return out

def _birdc(args: str) -> str:
    return _run(BIRD_CMD + args.split())

RID_RE        = re.compile(r"Router ID is (\d+\.\d+\.\d+\.\d+)")
LOCAL_AS_RE   = re.compile(r"^\s*Local AS:\s*(\d+)\s*$", re.I)

# Inside "show protocols all <name>"
NEIGH_ADDR_RE = re.compile(r"^\s*Neighbor address:\s*([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)\s*$", re.I)
NEIGH_ASN_RE  = re.compile(r"^\s*Neighbor AS:\s*(\d+)\s*$", re.I)
PEER_ID_RE    = re.compile(r"^\s*Neighbor ID:\s*([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)\s*$", re.I)
STATE_RE      = re.compile(r"^\s*BGP state:\s*(\S+)", re.I)

LINE_RE       = re.compile(r"^\s*(\S+)\s+BGP\s+\S+\s+(\S+)\s+", re.I)  # <name> ... <state> ...

def get_router_id() -> str:
    try:
        out = _birdc("show status")
        m = RID_RE.search(out)
        return m.group(1) if m else "0.0.0.0"
    except Exception:
        return "0.0.0.0"

def get_local_as(default_as: int = 65000) -> int:
    try:
        out = _birdc("show protocols all")
        m = LOCAL_AS_RE.search(out)
        return int(m.group(1)) if m else default_as
    except Exception:
        return default_as

def _is_ipv4(s: str) -> bool:
    try:
        return isinstance(ipaddress.ip_address(s), ipaddress.IPv4Address)
    except Exception:
        return False

def list_peers():
    """Return [{name, ip, state, asn, peer_id, in_updates, out_updates}, ...] (IPv4 only)."""
    peers = []
    try:
        base = _birdc("show protocols")
    except Exception:
        return peers

    names = []
    for line in base.splitlines():
        m = LINE_RE.match(line)
        if m:
            names.append((m.group(1), m.group(2)))

    for name, st in names:
        ip = None; asn = 0; state = st; peer_id = None
        try:
            detail = _birdc(f"show protocols all {name}")
        except Exception:
            detail = ""

        for dl in detail.splitlines():
            dl = dl.rstrip()
            if  (m := NEIGH_ADDR_RE.match(dl)): ip = m.group(1)
            elif(m := NEIGH_ASN_RE.match(dl)):  asn = int(m.group(1))
            elif(m := PEER_ID_RE.match(dl)):    peer_id = m.group(1)
            elif(m := STATE_RE.match(dl)):      state = m.group(1)

        if not (ip and _is_ipv4(ip)):
            # Skip non-IPv4 or missing addresses for BGP4-MIB
            continue

        peers.append({
            "name": name,
            "ip": ip,
            "state": state,
            "asn": asn,
            "peer_id": peer_id or ip,
            "in_updates": 0,
            "out_updates": 0,
        })

    log.info("Parsed %d IPv4 peers: %s", len(peers), peers)
    return peers

def snapshot(default_as: int = 65000):
    return {
        "router_id": get_router_id(),
        "local_as": get_local_as(default_as),
        "peers": list_peers(),
    }

if __name__ == "__main__":
    logging.basicConfig(level=(logging.DEBUG if os.getenv("BIRD_DEBUG") else logging.INFO))
    print(json.dumps(snapshot(int(os.getenv("ASN_DEFAULT","65000"))), indent=2))
