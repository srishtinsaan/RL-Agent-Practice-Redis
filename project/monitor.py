import subprocess
import time
from project.generate_csv import write_row_csv
import redis
import json
r = redis.Redis(host='localhost', port=6379, decode_responses=True)

HASH_KEY = "mac_table"
ZSET_KEY = "mac_age"

"""
This script:
Collects live state from OVS (MAC entries, flood pressure, entry age)
"""

# =========================
# CONFIGURATION
# =========================

SWITCH           = "g0_s1"
print(f"Active Switch: {SWITCH}")

INTERVAL         = 3

MAX_MAC_CAPACITY = 20
MAX_ENTRY_AGE    = 300

AGING_DEFAULT    = 300

# =========================
# HELPER
# =========================

previous_snapshot = []

# =========================================================
# 1. MAC TABLE ENTRIES : all MAC table entries from a switch sw
# =========================================================

# sorted
def get_mac_table_entries(sw):
    macs = r.zrevrange("mac_age", 0, -1)

    result = []

    for mac in macs:
        val = r.hget(HASH_KEY, mac)
        if val:
            result.append((mac, json.loads(val)))

    return result

# =========================================================
# 2. FLOOD PRESSURE  
# =========================================================


def get_flood_pressure(sw):
    global previous_snapshot

    current_entries = get_mac_table_entries(sw)

    # convert list → set of MACs
    new_macs = set(mac for mac, _ in current_entries)

    prev_macs = set(previous_snapshot)

    total = len(new_macs)

    if total == 0:
        previous_snapshot = new_macs
        return 0.0

    flood = 0

    for mac in new_macs:
        if mac not in prev_macs:
            flood += 1

    previous_snapshot = new_macs

    return round(flood / total, 3)
# =========================================================
# 3. ENTRY AGE
# =========================================================

def get_average_entry_age(sw):
    data = r.hgetall(HASH_KEY)

    result = {}

    for mac, val in data.items():
        try:
            result[mac] = json.loads(val)
        except:
            continue

    if not result:
        return 0.0

    total_age = sum(entry.get("age", 0) for entry in result.values())
    avg_age = total_age / len(result)

    return round(avg_age, 3)
# =========================================================
# 4. NORMALIZATION
# =========================================================

def normalize(value, max_value):
    if max_value == 0:
        return 0
    return round(min(value / max_value, 1.0), 4)

# =========================================================
# MAIN MONITOR LOOP
# (used when running monitor.py standalone for data collection)
# =========================================================

def monitor(sw):
    print("\n========== SDN MONITOR STARTED ==========\n")
    data = []

    for n in range(100):

        # 1. MAC entries
        mac_entries = get_mac_table_entries(sw)

        current_entries = len(mac_entries)
        mac_fill = normalize(current_entries, MAX_MAC_CAPACITY)

        # 2. Flood pressure
        flood_pressure = get_flood_pressure(sw)

        # 3. Average age (FIXED)
        avg_age = get_average_entry_age(sw)
        age_score = normalize(avg_age, MAX_ENTRY_AGE)

        # 4. State vector
        state = [mac_fill, flood_pressure, age_score]

        print(
            f"[{n+1:3d}] State: "
            f"mac_fill={mac_fill} | "
            f"flood_pressure={flood_pressure} | "
            f"age_score={age_score}"
        )

        write_row_csv(state)
        time.sleep(INTERVAL)

    print(f"\nCollected {len(data)} states")
# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":
    monitor(SWITCH)
