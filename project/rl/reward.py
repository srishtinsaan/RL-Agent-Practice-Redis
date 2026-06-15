
def get_reward(
    old_fill,
    new_fill,
    old_flood,
    new_flood,
    old_age,
    new_age,
    action
):
    reward = 0

    # MAC FILL
    HIGH_FILL = 0.8
    CRITICAL_FILL = 0.95

    # FLOOD_P
    HIGH_FLOOD = 0.5

    # AGE

    # stale age threshold conditions :
    # timeout = 60 :: avg_age > 36
    # timeout = 300 :: avg_age > 180
    # timeout = 600 :: avg_age > 360
    stale_age_threshold = 0.6 

    # fresh age threshold conditions :
    # timeout = 60 :: avg_age > 12
    # timeout = 300 :: avg_age > 60
    # timeout = 600 :: avg_age > 120
    fresh_age_threshold = 0.2  

    fill_gain = old_fill - new_fill
    flood_gain = old_flood - new_flood
    age_gain = old_age - new_age


# ------- 
    if action == "REBALANCE":

        # reward
        if new_fill < old_fill:
            if old_fill > 0.8 and old_age > stale_age_threshold:
                reward += 7   
            elif old_fill > 0.8:
                reward += 5   
       
        # penalty
        elif new_fill > old_fill:
            reward -= 5   
        elif old_fill < 0.5 and old_flood == 0 and old_age < fresh_age_threshold:
            reward -= 3 
            
#----------------
    if action == "EVICT_ENTRY":

        # reward
        if old_age > stale_age_threshold:
            if old_fill > CRITICAL_FILL:
                reward += 7
            elif old_fill > HIGH_FILL:
                reward += 5

        # penalty
        elif old_fill < 0.5:
            reward -= 10
        elif old_age < fresh_age_threshold:
            reward -= 5

# ------------
    if action == "INCREASE_AGING":

        # reward
        if old_flood > HIGH_FLOOD:
            if old_fill > HIGH_FILL:
                reward += 7
            else:
                reward += 5

        # penalty
        elif old_flood == 0 and old_fill < 0.5:
            reward -= 5
        elif old_age < fresh_age_threshold:
            reward -= 3


# -------------


    if action == "DECREASE_AGING":

        # reward
        if old_fill < 0.5 and old_flood == 0:
            if old_age > stale_age_threshold:
                reward += 7
            else:
                reward += 5

        # penalty
        elif old_fill > HIGH_FILL:
            reward -= 7
        elif old_flood > HIGH_FLOOD:
            reward -= 5


# --------- 

    reward += (
        50 * flood_gain +
        10 * fill_gain +   
        5 * age_gain
    )

    # situation : for logging
    if new_fill >= 0.95:
        situation = "CRITICAL"
    elif new_fill >= 0.80:
        situation = "PREVENTIVE"
    else:
        situation = "NORMAL"

    # outcome : for logging
    if new_fill < old_fill and new_flood < old_flood:
        outcome = "improved"
    elif new_fill > old_fill or new_flood > old_flood:
        outcome = "degraded"
    else:
        outcome = "neutral"

    return reward, outcome, situation





    # action_cost = {
    #     0: 0.10,   # EVICT_ENTRY
    #     1: 0.05,   # INCREASE_AGING
    #     2: 0.05,   # DECREASE_AGING
    #     3: 0.01    # REBALANCE
    # }

    # reward -= action_cost.get(action, 0)

    # if new_fill >= 0.95:
    #     situation = "CRITICAL"
    #     reward -= 15

    # elif new_fill >= 0.80:
    #     situation = "PREVENTIVE"
    #     reward += 3

    # else:
    #     situation = "NORMAL"


    # if reward > 0:
    #     outcome = "improved"
    # elif reward < 0:
    #     outcome = "degraded"
    # else:
    #     outcome = "neutral"

    # return reward, outcome, situation