from project.monitor import get_mac_table_entries
import time

try:
    while True:
        entries = get_mac_table_entries("g0_s1")

        print("\033c") #reset terminal everysecond 
        print("RL MAC TABLE VIEW")
        print("-" * 70)

        if not entries:
            print("Entries : 0")
            time.sleep(1)
            continue

        print(f"Entries : {len(entries)}")

        oldest = max(entries, key=lambda x: int(x.get("age", 0)))

        for e in entries:
            marker = ""
            if e.get("mac") == oldest.get("mac"):
                marker = " <-- WILL BE EVICTED"

            print(
                f"Port {e.get('port')} | "
                f"{e.get('mac')} | "
                f"Age {e.get('age')}s"
                f"{marker}"
            )

        time.sleep(1)

except KeyboardInterrupt:
    print("\nStopped cleanly.")