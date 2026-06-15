import sys, os
import csv
sys.path.append(os.path.dirname(__file__))
from project.rl.env import LiveEnv
from project.rl.states import LiveStateEncoder
from project.rl.agent import QAgent

def save_final_qtable(agent, encoder, path='project/results/qtable/final_q_table.csv'):
    os.makedirs(os.path.dirname(path), exist_ok=True)

    bins = encoder.bins

    with open(path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'State_Index',
            'Mac_Bin',
            'Flood_Bin',
            'Age_Bin',
            'Mac_Range',
            'Flood_Range',
            'Age_Range',
            'Q_EVICT',
            'Q_INC_AGE',
            'Q_DEC_AGE',
            'Q_REBALANCE',
            'Best_Action'
        ])

        for state_idx in range(encoder.total_states()):

            # decode bucket tuple from flat index
            mac_bin   = state_idx // (bins * bins)
            flood_bin = (state_idx % (bins * bins)) // bins
            age_bin   =  state_idx % bins

            q = agent.get_q_values(state_idx)
            best_action = ['EVICT', 'INC_AGE', 'DEC_AGE', 'REBALANCE'][int(q.index(max(q)))]

            writer.writerow([
                state_idx,
                mac_bin,
                flood_bin,
                age_bin,
                encoder.get_bin_name(mac_bin),
                encoder.get_bin_name(flood_bin),
                encoder.get_bin_name(age_bin),
                round(q[0], 4),
                round(q[1], 4),
                round(q[2], 4),
                round(q[3], 4),
                best_action
            ])

    print(f"[QTABLE] Final Q-table saved → {path}")

def run_live_training(switch='g0_s0', episodes=200, steps_per_ep=30):
    # ep = 200
    # steps = 30
    
    env     = LiveEnv(switch=switch)
    encoder = LiveStateEncoder(bins=8)
    agent   = QAgent(states=encoder.total_states(), actions=4)

    log_path = 'project/results/logs/live_step_log.csv'
    os.makedirs('project/results/logs', exist_ok=True)

    # per step q table
    qtable_path = 'project/results/qtable/q_table.csv'
    os.makedirs('project/results/qtable', exist_ok=True)

    episode_log_path = 'project/results/logs/episode_log.csv'

    with open(log_path, 'w', newline='') as f:
        writer = csv.writer(f)      
        writer.writerow([
            'Episode',
            'Step',

            'mac_fill',
            'MAC_Count',
            'flood_pressure',
            'avg_age',

            'Situation',
            'State_Index',

            'Original_Action',
            'Executed_Action',
            'Action_Name',

            'Q_EVICT',
            'Q_INC_AGE',
            'Q_DEC_AGE',
            'Q_REBALANCE',

            'Chosen_By',
            'Outcome',
            'Reward',

            'Total_Ep_Reward',
            'Epsilon',

            'Port_Acted',
            'Evicted_MAC',

            'Old_MAC_Fill',
            'New_MAC_Fill',

            'Old_Flood',
            'New_Flood',

            'Old_Age',
            'New_Age'
            ])
    
    with open(qtable_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Q_EVICT',
            'Q_INC_AGE',
            'Q_DEC_AGE',
            'Q_REBALANCE'
            ])

    rewards_history = []

    
    
    # G
    with open(episode_log_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Episode', 'Discounted_G', 'Total_Reward', 'Epsilon'])

    for ep in range(episodes):
        state_info   = env.get_live_state()
        state_idx    = encoder.get_state_index(state_info)
        total_reward = 0
        episode_rewards = []

        for step in range(steps_per_ep):
            is_random, action             = agent.choose_action_with_flag(state_idx)
            
            old_state_info = state_info.copy()
            next_state_info, reward, info = env.step(action)
            next_state_idx                = encoder.get_state_index(next_state_info)
            executed_action               = info["executed_action"]

            # FIX: update on executed_action, not original action
            agent.update(state_idx, executed_action, reward, next_state_idx)

            q_values     = agent.get_q_values(state_idx)
            state_idx    = next_state_idx
            state_info   = next_state_info
            total_reward += reward
            episode_rewards.append(reward) #for discounted reward

            # LOG every step
            with open(log_path, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    ep + 1,
                    step + 1,

                    info['mac_fill'],
                    info['mac_count'],
                    info['flood_pressure'],
                    info['avg_age'],

                    info['situation'],
                    state_idx,

                    info['original_action'],
                    info['executed_action'],
                    info['action_name'],

                    round(q_values[0], 4),
                    round(q_values[1], 4),
                    round(q_values[2], 4),
                    round(q_values[3], 4),

                    'RANDOM' if is_random else 'GREEDY',

                    info['outcome'],
                    round(reward, 4),

                    round(total_reward, 4),
                    round(agent.epsilon, 4),

                    info.get('port_acted', 'N/A'),
                    info.get('evicted_mac', 'N/A'),

                    old_state_info["mac_fill"],
                    next_state_info["mac_fill"],

                    old_state_info["flood_pressure"],
                    next_state_info["flood_pressure"],

                    old_state_info["avg_age"],
                    next_state_info["avg_age"]
                ])

                state_info = next_state_info

            with open(qtable_path, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    round(q_values[0], 4),
                    round(q_values[1], 4),
                    round(q_values[2], 4),
                    round(q_values[3], 4),
                ])

            print(
                f"  Ep {ep+1} | Step {step+1} | "
                f"{info['action_name']:15s} | "
                f"{info['outcome']:20s} | "
                f"Reward: {reward:+.2f} | "
                f"ε: {agent.epsilon:.3f}"
            )
        
        # discounted return
        G = 0
        for r in reversed(episode_rewards):
            G = r + agent.gamma * G
        
        rewards_history.append(total_reward)
            
        print(f"Ep {ep+1} | Discounted Return G: {G:.4f}")

        with open(episode_log_path, 'a', newline='') as f:   
            writer = csv.writer(f)
            writer.writerow([ep+1, round(G, 4), round(total_reward, 4), round(agent.epsilon, 4)])

        with open(qtable_path, 'w', newline='') as f:
            writer = csv.writer(f)

            writer.writerow([
            'State_Index',
            'Q_EVICT',
            'Q_INC_AGE',
            'Q_DEC_AGE',
            'Q_REBALANCE'
            ])

            for state_idx in range(encoder.total_states()):

                q = agent.get_q_values(state_idx)

                writer.writerow([
                    state_idx,
                    round(q[0], 4),
                    round(q[1], 4),
                    round(q[2], 4),
                    round(q[3], 4)
                ])
        
        agent.decay_epsilon() 

    save_final_qtable(agent, encoder)
    return agent, encoder, rewards_history