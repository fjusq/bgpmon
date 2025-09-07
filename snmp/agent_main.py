import os, ipaddress, pyagentx3
from bird_source import get_local_as, get_router_id, iter_peers

BGP4_BASE = "1.3.6.1.2.1.15"
PEER_ENTRY = "3.1"
C = {"peerIdentifier":"1","peerState":"2","peerAdminStatus":"3","remoteAddr":"7","remoteAs":"9",
     "inUpdates":"10","outUpdates":"11","lastError":"14"}
STATE_MAP = {"idle":1,"connect":2,"active":3,"opensent":4,"openconfirm":5,"established":6}
def _idx(ip): return str(ipaddress.ip_address(ip))

class BgpUpdater(pyagentx3.Updater):
  def update(self):
    self.set_INTEGER("1.0", 4)
    self.set_INTEGER("2.0", int(os.getenv("ASN_DEFAULT", get_local_as())))
    self.set_IPADDRESS("3.0", get_router_id())
    for p in iter_peers():
      ip = p.get("ip","0.0.0.0"); idx = _idx(ip)
      state = STATE_MAP.get(str(p.get("state","idle")).lower(),1)
      self.set_IPADDRESS(f"{PEER_ENTRY}.{C['remoteAddr']}.{idx}", ip)
      self.set_INTEGER(   f"{PEER_ENTRY}.{C['peerState']}.{idx}", state)
      self.set_INTEGER(   f"{PEER_ENTRY}.{C['remoteAs']}.{idx}", int(p.get("asn",0)))
      self.set_IPADDRESS( f"{PEER_ENTRY}.{C['peerIdentifier']}.{idx}", p.get("peer_id", ip))
      self.set_COUNTER32( f"{PEER_ENTRY}.{C['inUpdates']}.{idx}", int(p.get("in_updates",0)))
      self.set_COUNTER32( f"{PEER_ENTRY}.{C['outUpdates']}.{idx}", int(p.get("out_updates",0)))
      self.set_OCTETSTRING(f"{PEER_ENTRY}.{C['lastError']}.{idx}", b"\x00\x00")

class Agent(pyagentx3.Agent):
  def setup(self): self.register(BGP4_BASE, BgpUpdater)

if __name__ == "__main__":
  pyagentx3.setup_logging()
  a = Agent(agentx=os.getenv("AGENTX_SOCKET", "tcp:bgpm-snmpd:705"))
  try: a.start()
  except KeyboardInterrupt: a.stop()
