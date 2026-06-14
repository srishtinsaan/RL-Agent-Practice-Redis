import time
import pandas as pd
from prometheus_client import start_http_server, Gauge

# CSV file path
CSV_FILE = "project/results/logs/episode_log.csv"

# Table metric
EPISODE_TABLE = Gauge(
    "rl_episode_table",
    "RL Episode Metrics Table",
    ["episode", "discounted_g", "total_reward", "epsilon"]
)


def update_metrics():
    try:
        # Read CSV
        df = pd.read_csv(CSV_FILE)

        if df.empty:
            print("CSV file is empty.")
            return

        # Remove old metrics before reloading
        EPISODE_TABLE.clear()

        # Export every row
        for _, row in df.iterrows():

            episode = str(row["Episode"])
            discounted_g = str(row["Discounted_G"])
            total_reward = str(row["Total_Reward"])
            epsilon = str(row["Epsilon"])

            EPISODE_TABLE.labels(
                episode=episode,
                discounted_g=discounted_g,
                total_reward=total_reward,
                epsilon=epsilon
            ).set(1)

        print(f"Exported {len(df)} episodes")

    except Exception as e:
        print(f"Error reading CSV: {e}")


def main():
    start_http_server(8001)
    print("Prometheus exporter running on http://localhost:8001/metrics")

    while True:
        update_metrics()
        time.sleep(1)


if __name__ == "__main__":
    main()