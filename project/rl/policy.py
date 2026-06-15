def policy(mac_fill, avg_age, flood_pressure):


    if mac_fill > 0.85 or flood_pressure > 0.9:
        return 0   # EVICT_ENTRY (LRU/LFU)


    if 0.70 <= mac_fill <= 0.85 or avg_age > 0.6:
        return 3   # REBALANCE


    if flood_pressure > 0.6 or (mac_fill > 0.7 and avg_age < 0.3):
        return 1   # INCREASE_AGING

    if flood_pressure < 0.3 and avg_age > 0.6 and mac_fill < 0.6:
        return 2   # DECREASE_AGING


    return 3   # REBALANCE (safe fallback)











# def policy(mac_fill, avg_age, flood_pressure):

#     if mac_fill > 0.85:
#         return "EVICT"

#     if 0.70 <= mac_fill <= 0.85:
#         return "REBALANCE"

#     if flood_pressure > 0.7 or (mac_fill > 0.7 and avg_age < 0.3):
#         return "INCREASE_AGING"

#     if flood_pressure < 0.3 and avg_age > 0.6:
#         return "DECREASE_AGING"

  