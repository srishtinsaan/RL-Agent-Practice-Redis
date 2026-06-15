import subprocess
import redis
import json
import time

from project.get_data import (
    get_mac_table,       
)

r = redis.Redis(host='localhost', port=6379, decode_responses=True)

AGING_HIGH = 600
AGING_LOW  = 60

SUPPRESSED_KEY = "suppressed_macs"
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
        return None

def get_suppressed_set():
    return {m.lower() for m in r.smembers(SUPPRESSED_KEY)}

def _delete_from_redis(mac):
    pipe = r.pipeline()

    # remove from active state
    pipe.hdel(HASH_KEY, mac)
    pipe.zrem(ZSET_KEY, mac)

    # suppress so it won't be re-imported from OVS
    pipe.sadd(SUPPRESSED_KEY, mac)

    pipe.execute()

    print(f"[EVICT] {mac} removed + suppressed")

def sync_redis_from_ovs(sw):
    mac_entries = get_mac_table(sw)
    pipe = r.pipeline()

    # 🔥 snapshot (ONE TIME READ)
    suppressed = get_suppressed_set()

    filtered = {}

    for mac, entry in mac_entries.items():

        mac = mac.lower()   # normalize (IMPORTANT)

        # ❌ DO NOT call is_suppressed()
        if mac in suppressed:
            continue

        stored = r.hget(HASH_KEY, mac)

        if stored:
            stored_data = json.loads(stored)
            entry["seen_count"] = stored_data.get("seen_count", 1)
        else:
            entry["seen_count"] = 1

        filtered[mac] = entry

        pipe.hset(HASH_KEY, mac, json.dumps(entry))
        pipe.zadd(ZSET_KEY, {mac: entry["age"]})

    pipe.execute()

    return filtered

def action_evict_entry(sw, flood_pressure):
    mac_entries = sync_redis_from_ovs(sw)   # ← sync first so seen_count exists

    if not mac_entries:
        return None

    policy = "LFU" if flood_pressure > 0.6 else "LRU"
    print(f"[EVICT] Policy={policy}, flood={flood_pressure:.3f}")

    if policy == "LRU":
        return init_lru_eviction(mac_entries)
    else:
        return init_lfu_eviction(mac_entries)

def init_lru_eviction(mac_entries):
    if not mac_entries:
        return None, None
    stale_mac, stale_entry = max(mac_entries.items(), key=lambda x: x[1].get("age", 0))
    _delete_from_redis(stale_mac)
    return stale_mac, stale_entry

def init_lfu_eviction(mac_entries):
    if not mac_entries:
        return None, None
    stale_mac, stale_entry = min(mac_entries.items(), key=lambda x: x[1].get("seen_count", 0))
    _delete_from_redis(stale_mac)
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

def action_rebalance_table(sw, target_size=10):   # ← sw param added
    mac_entries = sync_redis_from_ovs(sw)          # ← read from OVS not Redis
    current_entries = len(mac_entries)

    if current_entries <= target_size:
        print("[ACTION] REBALANCE — no cleanup needed")
        return 0

    remove_count = current_entries - target_size

    scored = []
    for mac, entry in mac_entries.items():
        score = calculate_importance(entry)
        scored.append((mac, score))

    scored.sort(key=lambda x: x[1])   # least important first

    removed = 0
    for mac, _ in scored[:remove_count]:
        _delete_from_redis(mac)        # ← delete from Redis
        removed += 1

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
        action_rebalance_table(sw)     # ← pass sw
    else:
        print(f"[EXECUTE] Unknown action: {action_idx}")

    return evicted_mac