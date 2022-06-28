import torch
import random
import numpy as np
from RLFlappyBird import Bird, Pipe, Base, Game
from collections import deque
from model import Linear_QNet, QTrainer
from Plotter import plot

MAX_MEMORY = 100000
BATCH_SIZE = 1000
LR = 0.001

class Agent:

    def __init__(self):
        self.n_games = 0
        self.epsilon = 0
        self.gamma = 0.9
        self.memory = deque(maxlen=MAX_MEMORY)
        self.model = Linear_QNet(8, 156, 2)
        self.trainer = QTrainer(self.model, lr = LR, gamma = self.gamma)

    def get_state(self, game):
        bird = game.bird
        pipes = game.pipes
        point_r = bird.x + 40, bird.y
        point_u = bird.x, bird.y - 40
        point_d = bird.x, bird.y + 40
        #print((pipes[0].bottom - 200, pipes[0].bottom - 40), (bird.x, bird.y))
        upper, lower = 145, 45
        state = [
            #Safe
            pipes[0].bottom - lower < bird.y < pipes[0].bottom - upper,

            #Danger on moving straight
            (point_r[0] == pipes[0].x) and
            ((point_r[1] < pipes[0].bottom - upper) or
            (point_r[1] > pipes[0].bottom - lower)),

            #Danger on falling down
            (point_d[0] == pipes[0].x) and
            ((point_d[1] < pipes[0].bottom - upper) or
            (point_d[1] > pipes[0].bottom - lower)),

            #Danger on moving up
            (point_u[0] == pipes[0].x) and
            ((point_u[1] < pipes[0].bottom - upper) or
            (point_u[1] > pipes[0].bottom - lower)),

            # Danger pipe top
            bird.y < pipes[0].bottom - upper,

            # Danger pipe bottom
            bird.y > pipes[0].bottom - lower,

            # Danger screen top
            bird.y < 5,

            # Danger screen bottom
            bird.y > 680,
            ]

        return np.array(state, dtype=int)

    def remember(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))

    def train_long_memory(self):
        if len(self.memory) > BATCH_SIZE:
            mini_sample = random.sample(self.memory, BATCH_SIZE)
        else:
            mini_sample = self.memory
        states, actions, rewards, next_states, dones = zip(*mini_sample)
        self.trainer.train_step(states, actions, rewards, next_states, dones)

    def train_short_memory(self, state, action, reward, next_state, done):
        self.trainer.train_step(state, action, reward, next_state, done)

    def get_action(self, state):
        self.epsilon = 80 - self.n_games
        final_move = [0, 0]
        if random.randint(0, 200) < self.epsilon:
            move = random.randint(0, 1)
            final_move[move] = 1
        else:
            state0 = torch.tensor(state, dtype = torch.float)
            prediction = self.model(state0)
            move = torch.argmax(prediction).item()
            final_move[move] = 1
        return final_move

def train():
    plot_scores = []
    plot_mean_scores = []
    total_score = 0
    record = 0
    agent = Agent()
    game = Game()

    while True:
        state_old = agent.get_state(game)

        final_move = agent.get_action(state_old)

        reward, done, score = game.main(final_move)
        state_new = agent.get_state(game)

        agent.train_short_memory(state_old, final_move, reward, state_new, done)

        agent.remember(state_old, final_move, reward, state_new, done)

        if not done:
            game.reset()
            agent.n_games += 1
            agent.train_long_memory()

            if score > record:
                record = score
                agent.model.save()

            print("Game: ", agent.n_games, "Score: ", score, "Record: ", record)

            plot_scores.append(score)
            total_score += score
            mean_score = total_score / agent.n_games
            plot_mean_scores.append(mean_score)
            plot(plot_scores, plot_mean_scores)

if __name__ == '__main__':
    train()
