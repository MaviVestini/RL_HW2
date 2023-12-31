import random
import numpy as np
# import gymnasium as gym
# import time
# from gymnasium import spaces
# import os
import sklearn
import sklearn.pipeline
import sklearn.preprocessing
from sklearn.kernel_approximation import RBFSampler
import pickle


class VanillaFeatureEncoder:
    def __init__(self, env):
        self.env = env
        
    def encode(self, state):
        return state
    
    @property
    def size(self): 
        return self.env.observation_space.shape[0]

class RBFFeatureEncoder:
    def __init__(self, env): # modify
        self.env = env
        # TODO init rbf encoder
        self.n_components = 100

        # Scale parameter for the custom RBF encoder
        self.scale = 0.1

        # Get the extremes of the env space
        lows = self.env.unwrapped.low
        highs = self.env.unwrapped.high

        # Split the space in intervals both for the x and y axis
        x = np.linspace(lows[0], highs[0], 10)
        y = np.linspace(lows[1], highs[0], 10)

        # Put them together and define the centers as each possible couple x and y
        xs, ys = np.meshgrid(x, y)
        self.centers =  np.stack([xs.reshape(-1), ys.reshape(-1)], axis = 1)


    def encode(self, state): # modify
        # TODO use the rbf encoder to return the features
        # Compute and return the new features
        features = np.linalg.norm(state - self.centers, axis = 1) ** 2
        return np.exp(-features/(2*self.scale**2))

    @property   
    def size(self): # modify
        # TODO return the number of features
        return self.n_components



class TDLambda_LVFA:
    def __init__(self, env, feature_encoder_cls=RBFFeatureEncoder, alpha=0.01, alpha_decay=1, 
                gamma=0.9999, epsilon=0.3, epsilon_decay=0.995, final_epsilon=0.2, lambda_=0.9): # modify if you want (e.g. for forward view)
        self.env = env
        self.feature_encoder = feature_encoder_cls(env)
        self.shape = (self.env.action_space.n, self.feature_encoder.size)
        self.weights = np.random.random(self.shape)
        self.traces = np.zeros(self.shape)
        self.alpha = alpha
        self.alpha_decay = alpha_decay
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.final_epsilon = final_epsilon
        self.lambda_ = lambda_
        
    def Q(self, feats):
        feats = feats.reshape(-1,1)
        return self.weights@feats
    
    def update_transition(self, s, action, s_prime, reward, done): # modify
        s_feats = self.feature_encoder.encode(s)
        s_prime_feats = self.feature_encoder.encode(s_prime)
        # TODO update the weights
        
        # Compute the td error
        delta = reward + (1-done)*self.gamma*self.Q(s_prime_feats).max() - self.Q(s_feats)[action]
        
        # Update traces
        self.traces = self.gamma*self.lambda_*self.traces
        self.traces[action] += s_feats

        # Update weights
        self.weights[action] += self.alpha * delta * self.traces[action]


    def update_alpha_epsilon(self): # do not touch
        self.epsilon = max(self.final_epsilon, self.epsilon*self.epsilon_decay)
        self.alpha = self.alpha*self.alpha_decay
        
    def policy(self, state): # do not touch
        state_feats = self.feature_encoder.encode(state)
        return self.Q(state_feats).argmax()
    
    def epsilon_greedy(self, state, epsilon=None): # do not touch
        if epsilon is None: epsilon = self.epsilon
        if random.random()<epsilon:
            return self.env.action_space.sample()
        return self.policy(state)
    

    def train(self, n_episodes=200, max_steps_per_episode=200): # do not touch
        print(f'ep | eval | epsilon | alpha')
        for episode in range(n_episodes):
            done = False
            s, _ = self.env.reset()
            self.traces = np.zeros(self.shape)
            for i in range(max_steps_per_episode):
                
                action = self.epsilon_greedy(s)
                s_prime, reward, done, _, _ = self.env.step(action)
                self.update_transition(s, action, s_prime, reward, done)

                s = s_prime
                
                if done: break
                
            self.update_alpha_epsilon()

            if episode % 20 == 0:
                print(episode, self.evaluate(), self.epsilon, self.alpha)
                
    def evaluate(self, env=None, n_episodes=10, max_steps_per_episode=200): # do not touch
        if env is None:
            env = self.env
            
        rewards = []
        for episode in range(n_episodes):
            total_reward = 0
            done = False
            s, _ = env.reset()
            for i in range(max_steps_per_episode):
                action = self.policy(s)
                
                s_prime, reward, done, _, _ = env.step(action)
                
                total_reward += reward
                s = s_prime
                if done: break
            
            rewards.append(total_reward)
            
        return np.mean(rewards)

    def save(self, fname):
        with open(fname, 'wb') as f:
            pickle.dump(self, f)

    @classmethod
    def load(cls, fname):
        return pickle.load(open(fname,'rb'))
