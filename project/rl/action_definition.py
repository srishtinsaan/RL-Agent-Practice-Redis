import subprocess
import redis
import json

from project.monitor import get_mac_table_entries

r = redis.Redis(host='localhost', port=6379, decode_responses=True)



AGING_HIGH       = 600
AGING_LOW        = 60

HASH_KEY = "mac_table"
ZSET_KEY = "mac_age"

def run_cmd(cmd):
    try:
        result = subprocess.check_output(cmd, shell=True, text=True)
        return result.strip()

    except subprocess.CalledProcessError as e:
        print("\n[WARN] Command failed")
        print("CMD:", e.cmd)
        print("Return code:", e.returncode)
        print("STDERR:", e.stderr)

        # IMPORTANT: don't crash RL training
        return None

def action_evict_entry(sw, policy="LRU"):
    mac_entries = get_mac_table_entries(sw)

    if not mac_entries:
        print("[EVICT] No MAC entries found")
        return None

    if policy == "LRU":
        stale_mac, stale_entry = init_lru_eviction(mac_entries)

    elif policy == "LFU":
        stale_mac, stale_entry = init_lfu_eviction(mac_entries)

    else:
        print("[EVICT] Unknown policy")
        return None

    if not stale_mac:
        return None

    print(
        f"[EVICT-{policy}] MAC {stale_mac} "
        f"(age={stale_entry.get('age', 0)}, seen={stale_entry.get('seen_count', 0)})"
    )

    # IMPORTANT: actually apply eviction to Redis
    pipe = r.pipeline()
    pipe.hdel(HASH_KEY, stale_mac)
    pipe.zrem(ZSET_KEY, stale_mac)
    pipe.execute()

    return stale_mac

def init_lru_eviction(mac_entries):
    if not mac_entries:
        return None, None
    stale_mac, stale_entry = max(mac_entries, key=lambda x: x[1].get("age", 0))
    return stale_mac, stale_entry

def init_lfu_eviction(mac_entries):
    if not mac_entries:
        return None, None
    stale_mac, stale_entry = min(mac_entries, key=lambda x: x[1].get("seen_count", 0))
    return stale_mac, stale_entry

def action_increase_aging(sw):

    new_limit = AGING_HIGH

    r.set("mac_aging_limit", new_limit)

    run_cmd(f"ovs-vsctl set Bridge {sw} other-config:mac-aging-time={new_limit}")

    print(f"[ACTION] INCREASE_AGING → set limit = {new_limit}")

    return new_limit

def action_decrease_aging(sw):

    new_limit = AGING_LOW

    r.set("mac_aging_limit", new_limit)

    run_cmd(f"ovs-vsctl set Bridge {sw} other-config:mac-aging-time={new_limit}")

    print(f"[ACTION] DECREASE_AGING → set limit = {new_limit}")

    return new_limit

def calculate_importance(entry, protected_ports=None):
    if protected_ports is None:
        protected_ports = []

    port = entry.get("port", "")

    if port in protected_ports:
        return float('inf')

    age = entry.get("age", 0)
    seen_count = entry.get("seen_count", 1)

    return seen_count + (age * 0.01)

def action_rebalance_table(target_utilization=0.5, protected_ports=None):
    if protected_ports is None:
        protected_ports = []

    current_count = r.hlen(HASH_KEY)

    target_size = max(1, int(current_count * target_utilization))

    if current_count <= target_size:
        print("[ACTION] REBALANCE — no cleanup needed")
        return 0, []

    remove_count = current_count - target_size

    all_data = r.hgetall(HASH_KEY)

    entries = []

    for mac, raw in all_data.items():
        try:
            entry = json.loads(raw)
        except:
            continue

        score = calculate_importance(entry, protected_ports)
        entries.append((mac, score))

    entries.sort(key=lambda x: x[1])

    pipe = r.pipeline()
    removed = 0
    removed_macs = []

    for mac, _ in entries[:remove_count]:
        pipe.hdel(HASH_KEY, mac)
        pipe.zrem(ZSET_KEY, mac)
        removed_macs.append(mac)
        removed += 1

    pipe.execute()

    print(f"[ACTION] REBALANCE — removed {removed} entries: {removed_macs}")

    return removed, removed_macs

def execute_action(sw, action_idx, protected_ports=None):
    if protected_ports is None:
        protected_ports = []

    evicted_mac = None

    if action_idx == 0:
        evicted_mac = action_evict_entry(sw, policy="LRU")
    elif action_idx == 1:
        action_increase_aging(sw)
    elif action_idx == 2:
        action_decrease_aging(sw)
    elif action_idx == 3:
        action_rebalance_table(protected_ports=protected_ports)  
    else:
        print(f"[EXECUTE] Unknown action: {action_idx}")

    return evicted_mac
