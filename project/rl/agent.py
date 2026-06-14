import numpy as np
import random
from project.rl.actions import ActionSpace

class QAgent:
    def __init__(self, states, actions=7, alpha=0.1, gamma=0.99):

        # alpha = 0.1
        # gamma = 0.99
 
        self.alpha, self.gamma = alpha, gamma
        self.epsilon = 1.0
        self.epsilon_min   = 0.01
        self.epsilon_decay = 0.985

        # fill table with 0 
        self.q_table = np.zeros((states, actions))

    def choose_action_with_flag(self, state):
        if random.uniform(0, 1) < self.epsilon:
            return True, random.randint(0, 6)    # is_random=True
        return False, np.argmax(self.q_table[state])  # is_random=False

    def update(self, s, a, r, s_next):
        old_val  = self.q_table[s, a]
        next_max = np.max(self.q_table[s_next])

        # Bellman equation
        # Q(s,a) = Q(s,a) + α [ r + γ maxQ(s',a') − Q(s,a) ]
        self.q_table[s, a] = old_val + self.alpha * (r + self.gamma * next_max - old_val)

    def decay_epsilon(self):
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

    def get_q_values(self, state):
        return self.q_table[state]

    def get_action_name(self, action_idx):
        return ActionSpace.get_action_name(action_idx)
