def get_reward(
    old_fill,
    new_fill,
    old_flood,
    new_flood,
    old_age,
    new_age,
    action
):
    

    fill_gain = old_fill - new_fill
    flood_gain = old_flood - new_flood
    age_gain = old_age - new_age


    reward = (
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