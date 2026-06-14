import time
import csv
from collections import deque
from prometheus_client import start_http_server, Gauge

CSV_FILE = "project/results/logs/live_step_log.csv"

# keep only last N rows in memory
BUFFER_SIZE = 200
buffer = deque(maxlen=BUFFER_SIZE)

rl_table = Gauge(
    "rl_live_step_table",
    "Buffered RL Table",
    [
        "episode", "step", "mac_fill", "mac_count", "flood_pressure",
        "age_score", "situation", "state_index", "original_action",
        "executed_action", "action_name", "q_learn", "q_evict",
        "q_flood", "q_block", "q_unblock", "q_inc_age", "q_dec_age",
        "chosen_by", "outcome", "reward", "total_ep_reward",
        "epsilon", "port_acted", "currently_blocked", "evicted_mac",
        "old_mac_fill", "new_mac_fill", "old_flood", "new_flood",
        "old_age", "new_age"
    ]
)


def load_into_buffer():
    buffer.clear()

    with open(CSV_FILE, "r") as f:
        reader = csv.DictReader(f)

        for row in reader:
            buffer.append(row)


def export_buffer():
    # IMPORTANT: clear old metrics first
    rl_table.clear()

    for row in buffer:
        rl_table.labels(
                episode=row["Episode"],
                step=row["Step"],
                mac_fill=row["mac_fill"],
                mac_count=row["MAC_Count"],
                flood_pressure=row["flood_pressure"],
                age_score=row["age_score"],
                situation=row["Situation"],
                state_index=row["State_Index"],
                original_action=row["Original_Action"],
                executed_action=row["Executed_Action"],
                action_name=row["Action_Name"],
                q_learn=row["Q_LEARN"],
                q_evict=row["Q_EVICT"],
                q_flood=row["Q_FLOOD"],
                q_block=row["Q_BLOCK"],
                q_unblock=row["Q_UNBLOCK"],
                q_inc_age=row["Q_INC_AGE"],
                q_dec_age=row["Q_DEC_AGE"],
                chosen_by=row["Chosen_By"],
                outcome=row["Outcome"],
                reward=row["Reward"],
                total_ep_reward=row["Total_Ep_Reward"],
                epsilon=row["Epsilon"],
                port_acted=row["Port_Acted"],
                currently_blocked=row["Currently_Blocked"],
                evicted_mac=row["Evicted_MAC"],
                old_mac_fill=row["Old_MAC_Fill"],
                new_mac_fill=row["New_MAC_Fill"],
                old_flood=row["Old_Flood"],
                new_flood=row["New_Flood"],
                old_age=row["Old_Age"],
                new_age=row["New_Age"],
            ).set(1)


def main():
    start_http_server(8002)
    print("[PROMETHEUS] Running on :8002")

    while True:
        load_into_buffer()     # step 1: read CSV
        export_buffer()        # step 2: expose only buffer
        time.sleep(2)          # slow refresh prevents freeze


if __name__ == "__main__":
    main()