import subprocess
import redis 
import json
import time 
import csv

r = redis.Redis(host='localhost', port=6379, decode_responses=True)
#print(r.ping()) 

with open("stat.csv", 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Occupancy',
            'Flood',
            'Age']) 
        
HASH_KEY = "mac_table"
ZSET_KEY = "mac_age"


SWITCH = "g0_s1"
DEFAULT_AGE = 300
DEFAULT_SIZE = 20

avg_age=0
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
    global avg_age

    mac_entries = get_mac_table(SWITCH)
    pipe = r.pipeline()

    old_macs = set(r.hkeys(HASH_KEY))
    new_macs = set(mac_entries.keys())

    # 1. ADD / UPDATE ENTRIES
    for mac, entry in mac_entries.items():
        stored = r.hget(HASH_KEY, mac)

        if stored:
            stored = json.loads(stored)

            old_age = stored.get("age", entry["age"])
            seen_count = stored.get("seen_count", 1)

            # Detect refresh
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

    all_data = {
        mac: json.loads(val)
        for mac, val in r.hgetall(HASH_KEY).items()
    }

    fill = mac_fill()
    fpressure = flood_pressure()
    agescore = get_ageScore()

    print(
            f"\nCurrent MAC Table, "
            f"Age Score: {agescore:.3f}, "
            f"Table Fill: {fill:.3f}, "
            f"Flood Pressure: {fpressure:.3f}"
        )
    print(f"{'MAC':<25} {'PORT':<10} {'AGE':<10} {'seen_count':<10}")
    print("-" * 60)
    with open("stat.csv", 'a', newline='') as f:
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

def get_ageScore() -> float:
    return round(avg_age/DEFAULT_AGE, 3)

def mac_fill() -> float:
    count = r.zcard("mac_age")
    return round(count/DEFAULT_SIZE,3)

def flood_pressure() -> float:
    global previous_snapshot

    new_entries = get_mac_table(SWITCH)

    prev_macs = set(previous_snapshot.keys())
    #print(prev_macs)
    
    new_macs = set(new_entries.keys())
    #print(new_macs)

    total = len(new_macs)
    if total == 0:
        return 0.0

    flood = 0

    for mac in new_macs:
        if mac not in prev_macs:
            flood += 1

    return round(flood / total, 3)



running = True
try:
    while running:
        previous_snapshot = get_mac_table(SWITCH)   # SAVE OLD STATE
        time.sleep(1)
        update()                                     # overwrite Redis
        current_snapshot = get_mac_table(SWITCH)
        print_table()
        #print("MAC table stored successfully")
        # action_increase_aging()

except KeyboardInterrupt:
    running = False
    print("You Exit!!!")