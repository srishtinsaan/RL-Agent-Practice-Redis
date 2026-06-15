import subprocess
import redis 
import json
import time 
import csv

r = redis.Redis(host='localhost', port=6379, decode_responses=True)
#print(r.ping()) 

# stats
import os

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
STATS_DIR = os.path.join(BASE_DIR, "network_stats")

# print(f"[DEBUG] BASE_DIR  = {BASE_DIR}")
# print(f"[DEBUG] STATS_DIR = {STATS_DIR}")

os.makedirs(STATS_DIR, exist_ok=True)
STAT_CSV  = os.path.join(STATS_DIR, "stat.csv")      

STAT_CSV = os.path.join(STATS_DIR, "stat.csv")

        
HASH_KEY = "mac_table"
ZSET_KEY = "mac_age"
SUPPRESSED_KEY = "suppressed_macs"
REJOIN_THRESHOLD = 3


SWITCH = "g0_s1"
DEFAULT_AGE = 300
DEFAULT_SIZE = 10
MAX_MAC_CAPACITY = 28

r.set("mac_aging_limit", DEFAULT_AGE)

previous_snapshot = {}

# Helper Function
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

def get_mac_table(sw_name):
    cmd = f"ovs-appctl fdb/show {sw_name}"
    output = run_cmd(cmd)
    #print(output)
    if not output:
        return {}

    entries = {}

    for line in output.splitlines()[1:]:

        parts = line.split()
        #print(parts)
        # skip headers or invalid lines
        if len(parts) < 3:
            continue

        try:
            port = parts[0]
            vlan = int(parts[1])
            mac = parts[2]
            age = int(parts[3])

            entries[mac]={
                "port": port,
                "mac": mac,
                "vlan": vlan,   # OVS FDB usually doesn't expose VLAN here
                "age": age
            }

        except:
            continue
    
    #print(entries)
    return entries

def update():
    avg_age = 0

    mac_entries = get_mac_table(SWITCH)
    pipe = r.pipeline()

    old_macs = set(r.hkeys(HASH_KEY))
    new_macs = set(mac_entries.keys())

    suppressed = r.smembers(SUPPRESSED_KEY)
    # 1. ADD / UPDATE ENTRIES
    for mac, entry in mac_entries.items():

        # Suppression Policy
        if mac in suppressed:
            if entry["age"] <= REJOIN_THRESHOLD:

                r.srem(SUPPRESSED_KEY, mac)

                print(f"[REJOIN] {mac} allowed back (age={entry['age']})")

                # IMPORTANT: DO NOT continue
                # let it go into normal Redis update flow

            else:
                continue

        # Existing Logic
        stored = r.hget(HASH_KEY, mac)

        if stored:

            stored = json.loads(stored)

            old_age = stored.get("age", entry["age"])
            seen_count = stored.get("seen_count", 1)

            if entry["age"] <= old_age:
                seen_count += 1

        else:
            seen_count = 1

        entry["seen_count"] = seen_count

        pipe.hset(HASH_KEY, mac, json.dumps(entry))
        pipe.zadd(ZSET_KEY, {mac: entry["age"]})

    # 2. DELETE REMOVED ENTRIES
    removed = old_macs - new_macs

    for mac in removed:
        pipe.hdel(HASH_KEY, mac)
        pipe.zrem(ZSET_KEY, mac)

    # 3. AVG AGE
    if mac_entries:
        total_age = sum(e["age"] for e in mac_entries.values())
        avg_age = round(total_age / len(mac_entries), 3)

    else:
        avg_age = 0

    pipe.execute()

def print_table():
    print("\033c")
    mac_entries = get_mac_table(SWITCH)

    all_data = {
        mac: json.loads(val)
        for mac, val in r.hgetall(HASH_KEY).items()
    }

    fill = mac_fill(mac_entries)
    fpressure = flood_pressure(mac_entries)
    agescore = get_ageScore(mac_entries)

    print(
            f"\nCurrent MAC Table, "
            f"Table Fill: {fill:.3f}, "
            f"Flood Pressure: {fpressure:.3f}, "
            f"Age Score: {agescore:.3f}, "
        )
    print(f"{'MAC':<25} {'PORT':<10} {'AGE':<10} {'seen_count':<10}")
    print("-" * 60)

    with open(STAT_CSV, 'a', newline='') as f:      # ← was missing
        writer = csv.writer(f)
        writer.writerow([
            f"{fill:.3f}",
            f"{fpressure:.3f}",
            f"{agescore:.3f}"
        ])

    for mac, score in r.zrevrange(ZSET_KEY, 0, -1, withscores=True):
        data = all_data.get(mac)

        if data:
            print(f"{data.get('port', ''):<10} {mac:<25} {data.get('age', 0):<10} {data.get('seen_count', 0):<10}")

def get_ageScore(mac_entries):
    if not mac_entries:
        return 0.0

    avg_age = sum(e["age"] for e in mac_entries.values()) / len(mac_entries)
    
    #When increase and decrease age works
    current_timeout = int(r.get("mac_aging_limit"))
    return normalize(avg_age, current_timeout)

def mac_fill(mac_entries):
    return normalize(len(mac_entries), MAX_MAC_CAPACITY)

def flood_pressure(new_entries, prev_entries=None):
    global previous_snapshot

    # previous snapshot (t-1)
    prev_macs = set((prev_entries if prev_entries is not None else previous_snapshot).keys())

    # current snapshot (t)
    new_macs = set(new_entries.keys())

    total = len(new_macs)
    if total == 0:
        return 0.0

    flood = 0

    for mac in new_macs:
        if mac not in prev_macs:
            flood += 1

    return round(flood / total, 3)

def normalize(value, max_value):
    if max_value == 0:
        return 0
    return round(min(value / max_value, 1.0), 4)

def get_normalized_state(sw, prev_entries=None):
    mac_entries = get_mac_table(sw)

    print(f"[DEBUG] sw={sw} redis_count={r.hlen(HASH_KEY)}")

    mac_fill_val = normalize(len(mac_entries), MAX_MAC_CAPACITY)

    flood_val    = flood_pressure(mac_entries, prev_entries)

    age_val      = get_ageScore(mac_entries)

    return mac_fill_val, flood_val, age_val, mac_entries 

def init_csv():
    with open(STAT_CSV, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Occupancy', 'Flood', 'Age'])

if __name__ == "__main__":
    init_csv() 
    running = True
    try:
        while running:
            previous_snapshot = get_mac_table(SWITCH)
            time.sleep(1)
            update()
            print_table()

    except KeyboardInterrupt:
        print("You Exit!!!")