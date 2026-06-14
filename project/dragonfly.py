from mininet.net import Mininet
        
def topology():
    net = Mininet(controller=None)

    g0_s0 = net.addSwitch('g0_s0')
    g0_s1 = net.addSwitch('g0_s1')
    g1_s0 = net.addSwitch('g1_s0')
    g1_s1 = net.addSwitch('g1_s1')
    g2_s0 = net.addSwitch('g2_s0')
    g2_s1 = net.addSwitch('g2_s1')

    #Switch connection
    net.addLink(g0_s0, g0_s1) 
    net.addLink(g1_s0, g1_s1) 
    net.addLink(g2_s0, g2_s1) 
    net.addLink(g0_s0, g1_s0) 
    net.addLink(g1_s0, g2_s0) 
    net.addLink(g0_s0, g2_s0)

    # Group 0
    g0_s0_h1 = net.addHost('g0_s0_h1', mac='00:00:00:00:00:01')
    g0_s0_h2 = net.addHost('g0_s0_h2', mac='00:00:00:00:00:02')
    g0_s0_h3 = net.addHost('g0_s0_h3', mac='00:00:00:00:00:03')

    g0_s1_h1 = net.addHost('g0_s1_h1', mac='00:00:00:00:01:01')
    g0_s1_h2 = net.addHost('g0_s1_h2', mac='00:00:00:00:01:02')
    g0_s1_h3 = net.addHost('g0_s1_h3', mac='00:00:00:00:01:03')

    # Group 1
    g1_s0_h1 = net.addHost('g1_s0_h1', mac='00:00:00:01:00:01')
    g1_s0_h2 = net.addHost('g1_s0_h2', mac='00:00:00:01:00:02')
    g1_s0_h3 = net.addHost('g1_s0_h3', mac='00:00:00:01:00:03')

    g1_s1_h1 = net.addHost('g1_s1_h1', mac='00:00:00:01:01:01')
    g1_s1_h2 = net.addHost('g1_s1_h2', mac='00:00:00:01:01:02')
    g1_s1_h3 = net.addHost('g1_s1_h3', mac='00:00:00:01:01:03')

    # Group 2
    g2_s0_h1 = net.addHost('g2_s0_h1', mac='00:00:00:02:00:01')
    g2_s0_h2 = net.addHost('g2_s0_h2', mac='00:00:00:02:00:02')
    g2_s0_h3 = net.addHost('g2_s0_h3', mac='00:00:00:02:00:03')

    g2_s1_h1 = net.addHost('g2_s1_h1', mac='00:00:00:02:01:01')
    g2_s1_h2 = net.addHost('g2_s1_h2', mac='00:00:00:02:01:02')
    g2_s1_h3 = net.addHost('g2_s1_h3', mac='00:00:00:02:01:03')

    # g0_s0
    net.addLink(g0_s0_h1, g0_s0)
    net.addLink(g0_s0_h2, g0_s0)
    net.addLink(g0_s0_h3, g0_s0)

    # g0_s1
    net.addLink(g0_s1_h1, g0_s1)
    net.addLink(g0_s1_h2, g0_s1)
    net.addLink(g0_s1_h3, g0_s1)

    # g1_s0
    net.addLink(g1_s0_h1, g1_s0)
    net.addLink(g1_s0_h2, g1_s0)
    net.addLink(g1_s0_h3, g1_s0)

    # g1_s1
    net.addLink(g1_s1_h1, g1_s1)
    net.addLink(g1_s1_h2, g1_s1)
    net.addLink(g1_s1_h3, g1_s1)

    # g2_s0
    net.addLink(g2_s0_h1, g2_s0)
    net.addLink(g2_s0_h2, g2_s0)
    net.addLink(g2_s0_h3, g2_s0)

    # g2_s1
    net.addLink(g2_s1_h1, g2_s1)
    net.addLink(g2_s1_h2, g2_s1)
    net.addLink(g2_s1_h3, g2_s1)

    return net

def discover_switch_ports(net, switch_name):
    """
    Returns:
    {
        'uplink_ports': [...],    
    }
    """

    sw = net.get(switch_name)

    uplink_ports = []

    for intf in sw.intfList():

        if intf.name == "lo":
            continue

        link = intf.link
        if link is None:
            continue

        if link.intf1 == intf:
            peer_intf = link.intf2
        else:
            peer_intf = link.intf1

        peer_node = peer_intf.node

        port_no = sw.ports[intf]

        if "_s" in peer_node.name and "_h" not in peer_node.name:
            uplink_ports.append(port_no)

    return {
        "uplink_ports": sorted(uplink_ports),
    }