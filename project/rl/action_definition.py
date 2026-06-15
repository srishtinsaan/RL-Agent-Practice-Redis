import subprocess
import redis
import json

from project.get_data import (
    get_mac_table,       
)

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

def action_evict_entry(sw, flood_pressure):

    mac_entries = get_mac_table(sw)

    if not mac_entries:
        return None

    if flood_pressure > 0.6:
        policy = "LFU"   
    else:
        policy = "LRU"   

    if policy == "LRU":
        return init_lru_eviction(mac_entries)

    else:
        return init_lfu_eviction(mac_entries)

def init_lru_eviction(mac_entries):
    if not mac_entries:
        return None, None
    stale_mac, stale_entry = max(mac_entries.items(), key=lambda x: x[1].get("age", 0))  # ← .items()
    return stale_mac, stale_entry

def init_lfu_eviction(mac_entries):
    if not mac_entries:
        return None, None
    stale_mac, stale_entry = min(mac_entries.items(), key=lambda x: x[1].get("seen_count", 0))  # ← .items()
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

def calculate_importance(entry):

    age = entry.get("age", 0)
    seen_count = entry.get("seen_count", 1)

    return seen_count + (age * 0.01)

def action_rebalance_table(target_size=10):

    current_entries = r.hlen(HASH_KEY)

    if current_entries <= target_size:
        print("[ACTION] REBALANCE — no cleanup needed")
        return 0

    remove_count = current_entries - target_size

    entries = []

    for mac, raw in r.hgetall(HASH_KEY).items():

        try:
            entry = json.loads(raw)
        except:
            continue

        score = calculate_importance(entry)

        entries.append((mac, score))

    entries.sort(key=lambda x: x[1])

    pipe = r.pipeline()
    removed = 0

    for mac, _ in entries[:remove_count]:

        pipe.hdel(HASH_KEY, mac)
        pipe.zrem(ZSET_KEY, mac)

        removed += 1

    pipe.execute()

    print(f"[ACTION] REBALANCE — removed {removed} entries")

    return removed

def execute_action(sw, action_idx, flood_pressure):

    evicted_mac = None

    if action_idx == 0:
        evicted_mac = action_evict_entry(sw, flood_pressure)
    elif action_idx == 1:
        action_increase_aging(sw)
    elif action_idx == 2:
        action_decrease_aging(sw)
    elif action_idx == 3:
        action_rebalance_table()  
    else:
        print(f"[EXECUTE] Unknown action: {action_idx}")

    return evicted_mac
