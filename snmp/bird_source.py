# snmp/bird_source.py
import os, subprocess, re, ipaddress

BIRD_SOCK = os.getenv("BIRD_SOCK", None)

def _birdc(cmd: str) -> str:
    base = ["birdc"]
    if BIRD_SOCK:
        base += ["-s", BIRD_SOCK]
    return subprocess.check_output(base + cmd.split(), text=True)

RID_RE = re.compile(r"Router ID is (\d+\.\d+\.\d+\.\d+)")
AS_RE  = re.compile(r"Local AS number (\d+)", re.IGNORECASE)

def get_router_id() -> str:
    try:
        out = _birdc("show status")
        m = RID_RE.search(out)
        return m.group(1) if m else "0.0.0.0"
    except Exception:
        return "0.0.0.0"

def get_local_as() -> int:
    try:
        out = _birdc("show protocols all")
        m = AS_RE.search(out)
        return int(m.group(1)) if m else int(os.getenv("ASN_DEFAULT", "65000"))
    except Exception:
        return int(os.getenv("ASN_DEFAULT", "65000"))

def list_peers():
    """Return a list of peers with minimal fields."""
    peers = []
    try:
        out = _birdc("show protocols")
    except Exception:
        return peers

    for line in out.splitlines():
        parts = line.strip().split()
        if len(parts) >= 3 and parts[1] == "BGP":
            name = parts[0]
            state = "Established" if parts[2] == "up" else "Idle"
            ip = "0.0.0.0"
            asn = 0
            try:
                detail = _birdc(f"show protocols all {name}")
                for dl in detail.splitlines():
                    s = dl.strip()
                    if s.lower().startswith("neighbor "):
                        maybe = s.split()[1]
                        try:
                            ipaddress.ip_address(maybe)
                            ip = maybe
                        except ValueError:
                            pass
                    if "neighbor AS" in s or "neighbor as" in s:
                        try:
                            asn = int(s.split()[-1])
                        except Exception:
                            pass
            except Exception:
                pass
            peers.append({
                "ip": ip, "state": state, "asn": asn,
                "peer_id": ip, "in_updates": 0, "out_updates": 0
            })
    return peers

def iter_peers():
    for p in list_peers():
        yield p
