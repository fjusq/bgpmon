import os, ipaddress, pyagentx3
from bird_source import get_local_as, get_router_id, iter_peers

STATE_MAP = {"idle":1,"connect":2,"active":3,"opensent":4,"openconfirm":5,"established":6}
def _idx(ip): return str(ipaddress.ip_address(ip))

# ---- Scalars updater (register at 1.3.6.1.2.1.15) ----
class BgpScalars(pyagentx3.Updater):
    def update(self):
        # base = 1.3.6.1.2.1.15
        self.set_INTEGER("1.0", 4)  # bgpVersion.0
        try:
            local_as = int(os.getenv("ASN_DEFAULT", get_local_as()))
        except Exception:
            local_as = int(os.getenv("ASN_DEFAULT", "65000"))
        self.set_INTEGER("2.0", local_as)          # bgpLocalAs.0
        self.set_IPADDRESS("3.0", get_router_id()) # bgpIdentifier.0

# ---- Peer table updater (register at 1.3.6.1.2.1.15.3.1) ----
# Column numbers under bgpPeerEntry:
# 1=peerIdentifier (IpAddress), 2=peerState (INTEGER), 7=remoteAddr (IpAddress index), 9=remoteAs (Integer32)
# 10=inUpdates (Counter32), 11=outUpdates (Counter32), 14=lastError (OCTET STRING)
class BgpPeers(pyagentx3.Updater):
    def update(self):
        peers = list(iter_peers())
        # OPTIONAL: if you want to avoid a totally empty table during testing, add a fake row:
        # if not peers: peers = [{"ip":"127.0.0.2", "state":"idle", "asn":0, "peer_id":"127.0.0.2", "in_updates":0, "out_updates":0}]
        for p in peers:
            ip = p.get("ip","0.0.0.0")
            idx = _idx(ip)
            state = STATE_MAP.get(str(p.get("state","idle")).lower(), 1)
            asn = int(p.get("asn", 0))
            in_upd = int(p.get("in_updates", 0))
            out_upd = int(p.get("out_updates", 0))
            peer_id = p.get("peer_id", ip)

            # index + columns relative to 1.3.6.1.2.1.15.3.1
            self.set_IPADDRESS(f"7.{idx}", ip)            # remoteAddr (INDEX)
            self.set_INTEGER(  f"2.{idx}", state)         # peerState
            self.set_INTEGER(  f"9.{idx}", asn)           # remoteAs
            self.set_IPADDRESS(f"1.{idx}", peer_id)       # peerIdentifier
            self.set_COUNTER32(f"10.{idx}", in_upd)       # inUpdates
            self.set_COUNTER32(f"11.{idx}", out_upd)      # outUpdates
            self.set_OCTETSTRING(f"14.{idx}", b"\x00\x00")# lastError

class Agent(pyagentx3.Agent):
    def setup(self):
        # Register scalars only on the BGP root
        self.register("1.3.6.1.2.1.15", BgpScalars)
        # Register the peer table subtree explicitly
        self.register("1.3.6.1.2.1.15.3.1", BgpPeers)

if __name__ == "__main__":
    pyagentx3.setup_logging()
    a = pyagentx3.Agent()
    try: a.start()
    except KeyboardInterrupt: a.stop()
