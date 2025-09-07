# Minimal BGP4-MIB subset (1.3.6.1.2.1.15)
BGP4 = (1,3,6,1,2,1,15)

# Scalars (suffix .0)
bgpVersion     = BGP4 + (1,)
bgpLocalAs     = BGP4 + (2,)
bgpIdentifier  = BGP4 + (3,)

# Tables
# bgpPeerTable    = .15.3
# bgpPeerEntry    = .15.3.1 with index = bgpPeerRemoteAddr (IpAddress)
bgpPeerTable                    = BGP4 + (3,)
bgpPeerEntry                    = BGP4 + (3,1)
bgpPeerIdentifier               = BGP4 + (3,1,1)  # DisplayString (peer ID / RID)
bgpPeerState                    = BGP4 + (3,1,2)  # INTEGER { idle(1), connect(2), active(3), opensent(4), openconfirm(5), established(6) }
bgpPeerAdminStatus              = BGP4 + (3,1,3)  # INTEGER { stop(1), start(2) }
bgpPeerRemoteAddr               = BGP4 + (3,1,7)  # IpAddress
bgpPeerLastError                = BGP4 + (3,1,14) # OCTET STRING (2-octet error/suberror)
bgpPeerInUpdates                = BGP4 + (3,1,9)
bgpPeerOutUpdates               = BGP4 + (3,1,10)

STATE_MAP = {
    "Idle": 1, "Connect": 2, "Active": 3, "OpenSent": 4, "OpenConfirm": 5, "Established": 6
}
