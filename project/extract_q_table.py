import csv
from collections import defaultdict

def extract_final_qtable(
    log_path='project/results/logs/live_step_log.csv',
    out_path='project/results/qtable/final_q_table.csv',
    bins=8
):
    def get_bin_name(b):
        edges = [i/bins for i in range(bins+1)]
        return f"{edges[b]:.2f}-{edges[b+1]:.2f}"

    q_per_state = defaultdict(list)

    with open(log_path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            state_idx = int(row['State_Index'])
            q = [
                float(row['Q_EVICT']),
                float(row['Q_INC_AGE']),
                float(row['Q_DEC_AGE']),
                float(row['Q_REBALANCE'])
            ]
            q_per_state[state_idx].append(q)

    q_avg = {}
    for state_idx, q_list in q_per_state.items():
        n = len(q_list)
        q_avg[state_idx] = [
            round(sum(q[i] for q in q_list) / n, 4)
            for i in range(4)
        ]

    import os
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    with open(out_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'State_Index',
            'Mac_Bin', 'Flood_Bin', 'Age_Bin',
            'Mac_Range', 'Flood_Range', 'Age_Range',
            'Q_EVICT', 'Q_INC_AGE', 'Q_DEC_AGE', 'Q_REBALANCE',
            'Best_Action'
        ])

        for state_idx in range(bins ** 3):
            mac_bin   = state_idx // (bins * bins)
            flood_bin = (state_idx % (bins * bins)) // bins
            age_bin   = state_idx % bins

            q = q_avg.get(state_idx, [0.0, 0.0, 0.0, 0.0])
            best_action = ['EVICT', 'INC_AGE', 'DEC_AGE', 'REBALANCE'][q.index(max(q))]

            writer.writerow([
                state_idx,
                mac_bin, flood_bin, age_bin,
                get_bin_name(mac_bin),
                get_bin_name(flood_bin),
                get_bin_name(age_bin),
                q[0], q[1], q[2], q[3],
                best_action
            ])

    print(f"[QTABLE] Saved → {out_path} | States visited: {len(q_avg)}/{bins**3}")

if __name__ == '__main__':
    extract_final_qtable()