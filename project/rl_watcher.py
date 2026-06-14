import time
import os
import redis

# 1. Connect to the local Redis instance running on the standard system port
r = redis.Redis(host='localhost', port=6379, decode_responses=True)

# Relative path to the live log file based on the project folder root execution
CSV_FILE_PATH = "project/results/logs/live_step_log.csv"

def tail_csv_to_redis():
    print(f"[WATCHER] Active tracking initialized on target path:\n -> {os.path.abspath(CSV_FILE_PATH)}\n")
    
    # Gracefully wait until the RL agent training pipeline generates the directory or file
    while not os.path.exists(CSV_FILE_PATH):
        print("[WATCHER] Waiting for RL agent loop to create live_step_log.csv...")
        time.sleep(2)

    with open(CSV_FILE_PATH, "r") as f:
        # Read and cache the first line containing the column header maps
        header_line = f.readline()
        while not header_line.strip():
            # If the file exists but hasn't written the headers yet, wait a second
            time.sleep(0.5)
            f.seek(0)
            header_line = f.readline()
            
        header = header_line.strip().split(",")
        print(f"[WATCHER] Successfully mapped layout headers: {header}")
        
        # Move the file pointer tool straight to the end of the current file size
        # This prevents flooding database entries on older historical simulation iterations
        f.seek(0, os.SEEK_END)
        print("[WATCHER] Streaming data channel active. Monitoring incoming writes...\n")

        while True:
            line = f.readline()
            
            # If no new entry string is detected, wait a brief split second for the agent execution step
            if not line:
                time.sleep(0.1)
                continue
                
            # Clean whitespaces and strip the string by commas
            row_values = line.strip().split(",")
            if len(row_values) != len(header) or not row_values[0]:
                continue # Ignore broken, half-written or misaligned stream strings
                
            # Zip headers and data arrays directly into a single dictionary mapping object
            metrics_dict = dict(zip(header, row_values))
            
            # Write/overwrite the dictionary key matrix straight into a high-speed Redis Hash
            r.hset("rl_live_metrics", mapping=metrics_dict)
            
            print(f"[REDIS SYNC] Step: {metrics_dict.get('step', 'N/A')} | Reward: {metrics_dict.get('reward', 'N/A')} | Epsilon: {metrics_dict.get('epsilon', 'N/A')}")

if __name__ == "__main__":
    try:
        tail_csv_to_redis()
    except KeyboardInterrupt:
        print("\n[WATCHER] Monitoring terminated safely. Local storage pipeline disconnected.")
