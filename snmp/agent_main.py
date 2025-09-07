# agent_main.py
import os
import ipaddress
import pyagentx3

from bird_source import get_local_as, get_router_id, iter_peers
# ^ assume you already expose these; iter_peers should yield dicts like:
# {"ip": "10.0.0.2", "state": "established", "asn": 64512,
#  "in_updates": 12, "out_updates": 7, "peer_id": "10.0.0.2"}

BGP4_BASE = "1.3.6.1.2.1.15"          # bgp(15)
PEER_ENTRY = "3.1"                    # bgpPeerTable(3).bgpPeerEntry(1)

# BGP4-MIB column numbers (under bgpPeerEntry):
C = {
    "peerIdentifier": "1",            # IpAddress
    "peerState": "2",                 # INTEGER idle(1)..established(6)
    "peerAdminStatus": "3",           # INTEGER stop(1), start(2)
    "negotiatedVersion": "4",         # Integer32
    "localAddr": "5",                 # IpAddress
    "localPort": "6",                 # Integer32(0..65535)
    "remoteAddr": "7",                # IpAddress (TABLE INDEX)
    "remotePort": "8",                # Integer32(0..65535)
    "remoteAs": "9",                  # Integer32
    "inUpdates": "10",                # Counter32
    "outUpdates": "11",               # Counter32
    "inTotalMsgs": "12",              # Counter32
    "outTotalMsgs": "13",             # Counter32
    "lastError": "14",                # OCTET STRING (SIZE 2)
}

STATE_MAP = {
    "idle": 1, "connect": 2, "active": 3,
    "opensent": 4, "openconfirm": 5, "established": 6,
}

def ip_index(ip: str) -> str:
    # IpAddress index is appended as dotted-decimal octets
    return str(ipaddress.ip_address(ip))

class BgpUpdater(pyagentx3.Updater):
    def update(self):
        # Scalars (relative to 1.3.6.1.2.1.15):
        # bgpVersion(1).0, bgpLocalAs(2).0, bgpIdentifier(3).0
        self.set_INTEGER("1.0", 4)                                 # bgpVersion = 4
        self.set_INTEGER("2.0", int(os.getenv("ASN_DEFAULT", get_local_as())))
        self.set_IPADDRESS("3.0", get_router_id())

        # Table rows keyed by bgpPeerRemoteAddr (IpAddress)
        # Each instance OID is: <PEER_ENTRY>.<column>.<ip-as-dotted>
        for p in iter_peers():
            ip = ip_index(p["ip"])
            # mandatory columns
            self.set_IPADDRESS(f"{PEER_ENTRY}.{C['remoteAddr']}.{ip}", p["ip"])
            self.set_INTEGER(f"{PEER_ENTRY}.{C['peerState']}.{ip}", STATE_MAP.get(p["state"].lower(), 1))
            self.set_INTEGER(f"{PEER_ENTRY}.{C['remoteAs']}.{ip}", int(p["asn"]))

            # best-effort columns
            self.set_IPADDRESS(f"{PEER_ENTRY}.{C['peerIdentifier']}.{ip}", p.get("peer_id", p["ip"]))
            self.set_COUNTER32(f"{PEER_ENTRY}.{C['inUpdates']}.{ip}", int(p.get("in_updates", 0)))
            self.set_COUNTER32(f"{PEER_ENTRY}.{C['outUpdates']}.{ip}", int(p.get("out_updates", 0)))
            # Optional others (leave 0/empty if unknown)
            # self.set_INTEGER(f"{PEER_ENTRY}.{C['negotiatedVersion']}.{ip}", 4)

class Agent(pyagentx3.Agent):
    def setup(self):
        # Register the entire BGP subtree to us. Net-SNMP doesn't implement BGP4-MIB by default,
        # so there’s no conflict. If you want to be surgical, you could register only .2 and .3.
        self.register(BGP4_BASE, BgpUpdater)

if __name__ == "__main__":
    pyagentx3.setup_logging()
    agentx_addr = os.getenv("AGENTX_SOCKET", "tcp:bgpm-snmpd:705")
    a = Agent(agentx=agentx_addr)   # <-- pass socket explicitly
    try:
        a.start()
    except KeyboardInterrupt:
        a.stop()