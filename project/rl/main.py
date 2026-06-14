import sys, os
sys.path.append(os.path.dirname(__file__))
from project.rl.train import run_live_training
# from project.rl.states import LiveStateEncoder

if __name__ == "__main__":

    SWITCH   = 'g0_s1'
    EPISODES = 200
    STEPS    = 30

    try:
        agent, encoder, rewards_history = run_live_training(
            switch=SWITCH,
            episodes=EPISODES,
            steps_per_ep=STEPS
        )
    except KeyboardInterrupt:
        print("\nTraining interrupted by user.")

    # # Test - BINS
    # encoder = LiveStateEncoder()
    # encoder.display_bins_with_intervals()
