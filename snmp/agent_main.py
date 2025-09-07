import os
from pyagentx3.agent import Agent
from pyagentx3.objects import Integer, OctetString, IpAddress, Table, Column
from bgp4_mib_map import *
import bird_source

AGENTX_SOCKET = os.getenv("AGENTX_SOCKET", "/agentx/master")

class BgpPeerTable(Table):
    # Index is bgpPeerRemoteAddr (IpAddress) => table OID ends with .<ip as 4 octets>
    index = (IpAddress,)

    # Columns (relative to bgpPeerEntry)
    columns = {
        1: Column(OctetString),   # bgpPeerIdentifier
        2: Column(Integer),       # bgpPeerState
        3: Column(Integer),       # bgpPeerAdminStatus
        7: Column(IpAddress),     # bgpPeerRemoteAddr
        9: Column(Integer),       # bgpPeerInUpdates
        10: Column(Integer),      # bgpPeerOutUpdates
        14: Column(OctetString),  # bgpPeerLastError (2 bytes)
    }

    def _load(self):
        self.clear()
        for p in bird_source.list_peers():
            idx = (p["remote_ip"],)
            self.addRow(idx, {
                1: p["peer_id"].encode(),
                2: STATE_MAP.get(p["state"], 1),
                3: 2 if p["admin"] == "start" else 1,
                7: p["remote_ip"],
                9: int(p["in_updates"]),
                10: int(p["out_updates"]),
                14: p["last_error"],
            })

def main():
    agent = Agent(AGENTX_SOCKET)

    # Scalars
    agent.register_scalar(bgpVersion + (0,), Integer(4))
    agent.register_scalar(bgpLocalAs + (0,), Integer(bird_source.get_local_as()))
    rid = bird_source.get_router_id()
    agent.register_scalar(bgpIdentifier + (0,), IpAddress(rid))

    # Table
    peer_table = BgpPeerTable(oid=bgpPeerEntry)
    agent.register_table(peer_table)

    # Periodically refresh table/scalars
    @agent.scheduled(5)   # refresh every 5 seconds (tune as needed)
    def refresh(_):
        agent.update_scalar(bgpLocalAs + (0,), Integer(bird_source.get_local_as()))
        agent.update_scalar(bgpIdentifier + (0,), IpAddress(bird_source.get_router_id()))
        peer_table._load()

    agent.serve_forever()

if __name__ == "__main__":
    main()
