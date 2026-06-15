# MONITOR 
# 1. get_mac_table_entries

# entries = get_mac_table_entries("g0_s1")
# print(entries)


# ------------------


# 2. get_flood_pressure

# from project.monitor import get_flood_pressure
# entries = get_flood_pressure("g0_s1")
# print(entries)

# 3. get_avg_age
# from project.monitor import get_average_entry_age
# entries = get_average_entry_age("g0_s1")
# print(entries)

# 4. monitor function : write data in output/network_stats.csv
# from project.rl.env import LiveEnv




# -----------actions

# 1. evict
# from project.rl.action_definition import action_evict_entry


from project.rl.action_definition import (
    action_increase_aging, 
    action_decrease_aging
    , action_evict_entry,
    action_rebalance_table
    )


if __name__ == "__main__":
    sw = "g0_s1"
    
    action_increase_aging(sw)
    action_decrease_aging(sw)
    # action_evict_entry(sw, policy="LFU")
    # action_evict_entry(sw, policy="LRU")

# REMOVED ENTRIES : REBALANCE ACTION
    # env = LiveEnv(switch="g0_s1")
    # # print("Uplink ports:", env.uplink_ports)
    # removed = action_rebalance_table(
    # target_utilization=0.5,
    # protected_ports=env.uplink_ports
    # )
    # print("Removed entries:", removed)
