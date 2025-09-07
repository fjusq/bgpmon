import os, subprocess, re, ipaddress

BIRD_SOCK = os.getenv("BIRD_SOCK", None)

def _birdc(cmd):
    base = ["birdc"]
    if BIRD_SOCK:
        base = ["birdc", "-s", BIRD_SOCK]
    out = subprocess.check_output(base + cmd.split(), text=True)
    return out

RID_RE = re.compile(r"Router ID is (\d+\.\d+\.\d+\.\d+)")
AS_RE  = re.compile(r"Local AS number (\d+)")
PEER_LINE = re.compile(r"^(?P<name>\S+)\s+BGP\s+\S+\s+(?P<state>up|down)\s+(?P<since>\S+)\s*(?P<info>.*)$")

def get_router_id():
    out = _birdc("show status")
    m = RID_RE.search(out)
    return m.group(1) if m else "0.0.0.0"

def get_local_as():
    out = _birdc("show protocols all")
    m = AS_RE.search(out)
    return int(m.group(1)) if m else int(os.getenv("ASN_DEFAULT", "65000"))

def list_peers():
    # Very rough first pass; refine with your config knowledge.
    out = _birdc("show protocols")
    peers = []
    for line in out.splitlines():
        m = PEER_LINE.match(line.strip())
        if not m:
            continue
        name = m.group("name")
        # Resolve remote IP for this peer:
        # Try `show protocols all <name>` and look for "neighbor <ip>"
        detail = _birdc(f"show protocols all {name}")
        ip = "0.0.0.0"
        for dl in detail.splitlines():
            dl = dl.strip()
            if dl.lower().startswith("neighbor "):
                maybe = dl.split()[1]
                try:
                    ipaddress.ip_address(maybe)
                    ip = maybe
                    break
                except ValueError:
                    pass
        state = "Established" if "up" in m.group("state") else "Idle"
        peers.append({
            "name": name,
            "remote_ip": ip,
            "state": state,
            "admin": "start",
            "in_updates": 0,
            "out_updates": 0,
            "last_error": b"\x00\x00",
            "peer_id": ip,  # or parse 'remote router ID' if known
        })
    return peers
