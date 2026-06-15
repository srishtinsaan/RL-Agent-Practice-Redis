import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import project.get_data as gd

SNAPSHOT_T0 = {
    "aa:bb:cc:dd:ee:01": {"port": "1", "mac": "aa:bb:cc:dd:ee:01", "vlan": 1, "age": 10},
    "aa:bb:cc:dd:ee:02": {"port": "2", "mac": "aa:bb:cc:dd:ee:02", "vlan": 1, "age": 20},
}

SNAPSHOT_T1 = {
    "aa:bb:cc:dd:ee:01": {"port": "1", "mac": "aa:bb:cc:dd:ee:01", "vlan": 1, "age": 11},
    "aa:bb:cc:dd:ee:03": {"port": "3", "mac": "aa:bb:cc:dd:ee:03", "vlan": 1, "age": 5},
}

call_count = 0

def mock_get_mac_table(sw_name):
    global call_count
    call_count += 1
    print(f"  [MOCK] get_mac_table() call #{call_count}")
    # TEST 1 doesn't call mock, so call #1 here = TEST 2's env call → return T1
    return SNAPSHOT_T1

# Patch on gd module so get_normalized_state inside get_data uses mock too
gd.get_mac_table = mock_get_mac_table

from project.rl.env import LiveEnv

# ─── TEST 1: compute expected values directly (no mock call) ───
print("\n========== TEST 1: get_data functions ==========")

fill_expected  = gd.normalize(len(SNAPSHOT_T1), gd.MAX_MAC_CAPACITY)
flood_expected = gd.flood_pressure(SNAPSHOT_T1, SNAPSHOT_T0)
age_expected   = gd.get_ageScore(SNAPSHOT_T1)

print(f"  Expected fill  : {fill_expected}")
print(f"  Expected flood : {flood_expected}")
print(f"  Expected age   : {age_expected}")

# ─── TEST 2: env.get_live_state() ───
print("\n========== TEST 2: env.get_live_state() ==========")

env = LiveEnv.__new__(LiveEnv)
env.switch = "g0_s1"
env.prev_mac_entries = SNAPSHOT_T0    # prev = T0, current will be T1 → flood = 0.5

state = env.get_live_state()

print(f"  env fill       : {state['mac_fill']}")
print(f"  env flood      : {state['flood_pressure']}")
print(f"  env age        : {state['avg_age']}")

# ─── COMPARISON ───
print("\n========== COMPARISON ==========")
print(f"  fill  match : {state['mac_fill']       == fill_expected}")
print(f"  flood match : {state['flood_pressure'] == flood_expected}")
print(f"  age   match : {state['avg_age']        == age_expected}")