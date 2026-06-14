import subprocess
import time
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from project.monitor import (
    get_mac_table_entries,
    get_flood_pressure,
    get_average_entry_age,
    normalize,
    MAX_MAC_CAPACITY,
    MAX_ENTRY_AGE
)

from project.rl.action_definition import execute_action

from project.rl.reward import get_reward
from project.rl.actions import ActionSpace

"""
    Reads live network state
    Applies RL actions safely (with guards)
    omputes reward + next state transition
"""

class LiveEnv:
    def __init__(self, switch=None):

        try:
            bridges = subprocess.check_output(
                ["ovs-vsctl", "list-br"], text=True
            ).split()
            if not bridges:
                raise RuntimeError(
                    "\n[ERROR] No OVS switches found.\n"
                    "Start Mininet first: sudo python3 dragonfly.py\n"
                    "Then run the RL agent in a separate terminal."
                )
            self.switch = switch or "g0_s1"
            print(f"[OK] Connected to switch: {self.switch}")

        except FileNotFoundError:
            raise RuntimeError(
                "\n[ERROR] ovs-vsctl not found.\n"
                "Are you running inside WSL with OVS installed?"
            )

        # load topology info
        import os
        import json

        BASE_DIR = os.path.dirname(os.path.abspath(__file__))

        file_path = os.path.join(BASE_DIR, "topology_info.json")

        with open(file_path, "r") as f:
            topology = json.load(f)

        self.uplink_ports = topology["uplink_ports"]
        
    def get_live_state(self):

        mac_entries = get_mac_table_entries(self.switch)

        mac_fill = normalize(len(mac_entries),MAX_MAC_CAPACITY)

        flood_pressure = get_flood_pressure(self.switch)

        avg_age = get_average_entry_age(self.switch)

        


        return {
            "mac_fill": mac_fill,
            "flood_pressure": flood_pressure,
            "avg_age": avg_age,
            "mac_entries": mac_entries
        }
    
    def step(self, action):

        state_info = self.get_live_state()

        original_action = action

    #
    # Guard:
    #
        # if action in [0, 1] and state_info["mac_fill"] < 0.20:
        #     print("[GUARD] Table too small for eviction")
        #     action = 2  # increase aging instead

        executed_action = action

        result = execute_action(self.switch, executed_action, protected_ports=self.uplink_ports)

        if executed_action in [0, 1]:
            time.sleep(3)
        else:
            time.sleep(1)

        next_state_info = self.get_live_state()

        fill_change = (
            next_state_info["mac_fill"]
            - state_info["mac_fill"]
        )

        flood_change = (
            next_state_info["flood_pressure"]
            - state_info["flood_pressure"]
        )

        print(
        f"[STATE] "
        f"Fill {state_info['mac_fill']:.3f}"
        f"->{next_state_info['mac_fill']:.3f} | "
        f"Flood {state_info['flood_pressure']:.3f}"
        f"->{next_state_info['flood_pressure']:.3f} | "
        f"Age {state_info['avg_age']:.3f}"
        f"->{next_state_info['avg_age']:.3f}"
        )

        reward, outcome, situation = get_reward(
            action=executed_action,

            old_fill=state_info["mac_fill"],
            new_fill=next_state_info["mac_fill"],

            old_flood=state_info["flood_pressure"],
            new_flood=next_state_info["flood_pressure"],

            old_age=state_info["avg_age"],
            new_age=next_state_info["avg_age"],

            all_ports_blocked=False
        )

    #
    # Penalty if eviction found nothing
    #
        if (
            executed_action in [0, 1]
            and result is None
        ):
            reward -= 1.0

        info = {
            "action_name":
                ActionSpace.get_action_name(
                executed_action
            ),

            "original_action":
                original_action,

            "executed_action":
                executed_action,

            "mac_count":
                len(next_state_info["mac_entries"]),

            "mac_fill":
                next_state_info["mac_fill"],

            "fill_change":
                round(fill_change, 4),

            "flood_pressure":
                next_state_info["flood_pressure"],

            "flood_change":
                round(flood_change, 4),

            "outcome":
                outcome,

            "situation":
                situation,

            "action_result":
                result if result else "N/A"
        }

        return next_state_info, reward, info