# snmp/agent_main.py
import os, time, threading, logging, ipaddress, pyagentx3
from bird_source import snapshot as bird_snapshot

log = logging.getLogger("bgpmon.snmp")
STATE_MAP = {"idle":1,"connect":2,"active":3,"opensent":4,"openconfirm":5,"established":6}

COLLECT_INTERVAL = int(os.getenv("COLLECT_INTERVAL", "15"))
ASN_DEFAULT = int(os.getenv("ASN_DEFAULT", "65000"))

class SharedState:
    def __init__(self):
        self.lock = threading.RLock()
        self.data = {"router_id":"0.0.0.0", "local_as": ASN_DEFAULT, "peers": []}
        self.updated = 0

STATE = SharedState()
STOP = threading.Event()

def collector_loop():
    log.info("Collector thread starting (interval=%ss)", COLLECT_INTERVAL)
    while not STOP.is_set():
        try:
            snap = bird_snapshot(ASN_DEFAULT)
            with STATE.lock:
                STATE.data = snap
                STATE.updated = time.time()
            log.info("Collector updated: rid=%s as=%s peers=%d",
                     snap.get("router_id"), snap.get("local_as"),
                     len(snap.get("peers",[])))
        except Exception as e:
            log.exception("Collector failed: %s", e)
        STOP.wait(COLLECT_INTERVAL)

def _is_ipv4(s: str) -> bool:
    try:
        return isinstance(ipaddress.ip_address(s), ipaddress.IPv4Address)
    except Exception:
        return False

# -------- Updaters read from cache ONLY (no subprocess calls here) --------
class BgpVersion(pyagentx3.Updater):
    # base 1.3.6.1.2.1.15.1
    def update(self): self.set_INTEGER("0", 4)

class BgpLocalAs(pyagentx3.Updater):
    # base 1.3.6.1.2.1.15.2
    def update(self):
        with STATE.lock:
            self.set_INTEGER("0", int(STATE.data.get("local_as", ASN_DEFAULT)))

class BgpIdentifier(pyagentx3.Updater):
    # base 1.3.6.1.2.1.15.4
    def update(self):
        with STATE.lock:
            rid = STATE.data.get("router_id", "0.0.0.0")
        # ensure valid IPv4 for IpAddress
        if not _is_ipv4(rid): rid = "0.0.0.0"
        self.set_IPADDRESS("0", rid)

class BgpPeers(pyagentx3.Updater):
    # base 1.3.6.1.2.1.15.3.1 (bgpPeerEntry)
    def update(self):
        with STATE.lock:
            peers = list(STATE.data.get("peers", []))

        if not peers:
            log.info("BgpPeers: empty cache -> endOfMib")
            return

        published = 0
        for p in peers:
            try:
                ip = p.get("ip")
                if not _is_ipv4(ip): 
                    continue
                idx = ip  # IpAddress index is dotted IPv4
                state = STATE_MAP.get(str(p.get("state","idle")).lower(), 1)
                self.set_IPADDRESS(f"7.{idx}", ip)                 # remoteAddr (INDEX)
                self.set_INTEGER(  f"2.{idx}", int(state))         # peerState
                self.set_INTEGER(  f"9.{idx}", int(p.get("asn",0)))# remoteAs
                self.set_IPADDRESS(f"1.{idx}", p.get("peer_id",ip))# peerIdentifier
                self.set_COUNTER32(f"10.{idx}", int(p.get("in_updates",0)))
                self.set_COUNTER32(f"11.{idx}", int(p.get("out_updates",0)))
                self.set_OCTETSTRING(f"14.{idx}", b"\x00\x00")
                published += 1
            except Exception as e:
                log.exception("BgpPeers: failed row %s: %s", p, e)
        log.info("BgpPeers: published %d rows", published)

class Agent(pyagentx3.Agent):
    def setup(self):
        # Scalars
        self.register("1.3.6.1.2.1.15.1", BgpVersion)     # bgpVersion.0
        self.register("1.3.6.1.2.1.15.2", BgpLocalAs)     # bgpLocalAs.0
        self.register("1.3.6.1.2.1.15.4", BgpIdentifier)  # bgpIdentifier.0
        # Table
        self.register("1.3.6.1.2.1.15.3.1", BgpPeers)     # bgpPeerEntry

if __name__ == "__main__":
    pyagentx3.setup_logging()
    logging.getLogger().setLevel(logging.INFO)

    # start collector thread
    t = threading.Thread(target=collector_loop, name="collector", daemon=True)
    t.start()

    a = Agent()
    try:
        a.start()
    except KeyboardInterrupt:
        STOP.set()
        a.stop()
        t.join(timeout=2)
