# auto_traffic.py

import time
import subprocess
import random


# ============================================================
# FDB REFRESH (UNCHANGED)
# ============================================================

def fdb_refresh_loop(switch_name, interval=1):
    """
    Continuously dump FDB for RL agent.
    """
    fdb_file = f"/tmp/fdb_{switch_name}.txt"

    while True:
        try:
            result = subprocess.run(
                ["ovs-appctl", "fdb/show", switch_name],
                capture_output=True,
                text=True
            )

            with open(fdb_file, "w") as f:
                f.write(result.stdout)

            lines = result.stdout.splitlines()
            entries = max(0, len(lines) - 1)

            print(f"[FDB] Entries={entries}")

        except Exception as e:
            print(f"[FDB ERROR] {e}")

        time.sleep(interval)


# ============================================================
# GROUP UTILITIES
# ============================================================

def get_host_group(host):
    """
    Extract dragonfly group from hostname.

    g0_s0_h1 -> 0
    g1_s1_h2 -> 1
    g2_s0_h3 -> 2
    """

    return host.name.split('_')[0]


def choose_destination(src, hosts, local_ratio):
    """
    Choose local/remote destination.

    local_ratio:
    0.9 -> 90% local
    0.7 -> 70% local
    0.5 -> 50% local
    0.0 -> uniform random
    """

    if local_ratio == 0.0:
        candidates = [h for h in hosts if h != src]
        return random.choice(candidates)

    src_group = get_host_group(src)

    local_hosts = [
        h for h in hosts
        if h != src and get_host_group(h) == src_group
    ]

    remote_hosts = [
        h for h in hosts
        if h != src and get_host_group(h) != src_group
    ]

    if random.random() < local_ratio:
        if local_hosts:
            return random.choice(local_hosts)

    if remote_hosts:
        return random.choice(remote_hosts)

    return random.choice([h for h in hosts if h != src])


# ============================================================
# FLOW DURATION GENERATION
# ============================================================

def get_flow_duration(flow_type):

    # Many short flows
    if flow_type == "short":
        return random.randint(5, 30)

    # Few long flows
    elif flow_type == "long":
        return random.randint(120, 300)

    # Heavy-tailed
    elif flow_type == "heavy":

        r = random.random()

        if r < 0.80:
            return random.randint(5, 20)

        elif r < 0.95:
            return random.randint(30, 60)

        else:
            return random.randint(120, 300)

    return 30


# ============================================================
# SCENARIOS
# ============================================================

SCENARIOS = [

    {
        "name": "90_LOCAL_SHORT",
        "local_ratio": 0.9,
        "flow_type": "short",
        "active_range": (4, 8)
    },

    {
        "name": "70_LOCAL_LONG",
        "local_ratio": 0.7,
        "flow_type": "long",
        "active_range": (8, 12)
    },

    {
        "name": "50_LOCAL_HEAVY",
        "local_ratio": 0.5,
        "flow_type": "heavy",
        "active_range": (12, 18)
    },

    {
        "name": "UNIFORM_RANDOM",
        "local_ratio": 0.0,
        "flow_type": "heavy",
        "active_range": (4, 18)
    }
]


# ============================================================
# BOOTSTRAP LEARNING
# ============================================================

def bootstrap_learning(net):

    print("[BOOTSTRAP] Initial MAC learning")

    hosts = net.hosts

    for src in hosts:

        candidates = [h for h in hosts if h != src]

        if not candidates:
            continue

        dst = random.choice(candidates)

        src.cmd(
            f"ping -c 1 {dst.IP()} > /dev/null 2>&1"
        )

    print("[BOOTSTRAP] Done")

    time.sleep(2)


# ============================================================
# SCENARIO EXECUTION
# ============================================================

def execute_scenario(net, scenario):

    hosts = net.hosts

    low, high = scenario["active_range"]

    active_count = random.randint(
        low,
        min(high, len(hosts))
    )

    active_hosts = random.sample(
        hosts,
        active_count
    )

    print("\n================================================")
    print(f"[SCENARIO] {scenario['name']}")
    print(f"Local Ratio : {scenario['local_ratio']}")
    print(f"Flow Type   : {scenario['flow_type']}")
    print(f"Active MACs : {active_count}")
    print("================================================\n")

    for src in active_hosts:

        dst = choose_destination(
            src,
            hosts,
            scenario["local_ratio"]
        )

        duration = get_flow_duration(
            scenario["flow_type"]
        )

        interval = random.choice([
            0.5,
            1,
            2
        ])

        src.cmd(
            f"timeout {duration} "
            f"ping -i {interval} {dst.IP()} "
            f"> /dev/null 2>&1 &"
        )

        print(
            f"{src.name} -> {dst.name} "
            f"| Duration={duration}s "
            f"| Interval={interval}s"
        )

# ============================================================
# MAIN TRAFFIC ENGINE
# ============================================================

def keepalive(net):

    print("\n[TRAFFIC] Scenario-based traffic engine started")

    bootstrap_learning(net)

    current_scenario = random.choice(SCENARIOS)

    last_change = time.time()

    execute_scenario(net, current_scenario)

    while True:

        now = time.time()

        #
        # Change scenario every 5 minutes
        #
        if now - last_change >= 300:

            current_scenario = random.choice(
                SCENARIOS
            )

            execute_scenario(
                net,
                current_scenario
            )

            last_change = now

        #
        # Small refresh every 20 seconds
        #
        if random.random() < 0.4:

            hosts = net.hosts

            src = random.choice(hosts)

            dst = choose_destination(
                src,
                hosts,
                current_scenario["local_ratio"]
            )

            src.cmd(
                f"ping -c 1 {dst.IP()} "
                f"> /dev/null 2>&1 &"
            )

        time.sleep(20)