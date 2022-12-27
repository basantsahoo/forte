from transition.markov_chain import MarkovChain
import numpy as np
import scipy.stats as ss
from collections import OrderedDict
open_type_codes = ['GAP_UP', 'GAP_DOWN', 'ABOVE_VA', 'BELOW_VA', 'INSIDE_VA']
intermediate_steps = ['D99', 'D29', 'D28', 'D27', 'D26', 'D25', 'D24', 'D23', 'D22', 'D21', 'D20', 'D19', 'D18', 'D17', 'D16', 'D15', 'D14', 'D13', 'D12', 'D11', 'D10', 'D9', 'D8', 'D7', 'D6', 'D5', 'D4', 'D3', 'D2', 'D1', 'POC', 'U1', 'U2', 'U3', 'U4', 'U5', 'U6', 'U7', 'U8', 'U9', 'U10', 'U11', 'U12', 'U13', 'U14', 'U15', 'U16', 'U17', 'U18', 'U19', 'U20', 'U21', 'U22', 'U23', 'U24', 'U25', 'U26', 'U27', 'U28', 'U29', 'U99']

class MarkovChainFirstLevel(MarkovChain):
    def build_transition_model(self, data, transitions):
        model = OrderedDict()
        model[self.prev_state] = {'count':0}
        for open_type_code in open_type_codes:
            model[open_type_code] = {'count':0}
            model[self.prev_state][open_type_code] = 0
        for tpo in range(1,14):
            for step in intermediate_steps:
                for mov in ['F', 'R']:
                    model[str(tpo) + "_" + step + "_" + mov] = {'count': 0}
        for (day, features) in data.items():
            model[features['open_type']]['count'] += 1
            model[self.prev_state][features['open_type']] += 1
            model[self.prev_state]['count'] += 1

            transition_list = features[transitions]
            for idx in range(len(transition_list) - 1):
                state = transition_list[idx]
                follow = transition_list[idx + 1]
                if not idx:
                    if state not in model[features['open_type']]:
                        model[features['open_type']][state] = 0
                    model[features['open_type']][state] += 1
                if state != follow:
                    if follow not in model[state]:
                        model[state][follow] = 0
                    model[state]['count'] += 1
                    model[state][follow] += 1
        self.model = model

    def calc_transition_freq(self):
        self.states = np.array(list(self.model.keys()))
        self.observed_matrix = np.zeros((len(self.states), len(self.states)))
        self.observed_p_matrix = np.zeros((len(self.states), len(self.states)))
        for x in range(len(self.states)):
            xid = np.argwhere(self.states == self.states[x]).flatten()
            transitions = self.model[self.states[x]]
            for to_state in list(transitions.keys()):
                yid = np.argwhere(self.states == to_state).flatten()
                cnt = transitions[to_state]
                self.observed_matrix[xid, yid] = cnt
                self.observed_p_matrix[xid, yid] = transitions['count'] and cnt/transitions['count'] or 0


    def from_data(self, data, transitions='observed_transitions'):
        # states list
        self.build_transition_model(data, transitions)
        self.calc_transition_freq()
        #self.observed_matrix = self.calc_transition_freq()
        #self._obs_row_totals = np.sum(self.observed_matrix, axis=1)
        # observed transition probability matrix
        #self.observed_p_matrix = np.nan_to_num(self.observed_matrix / self._obs_row_totals[:, None])
        # filling in a row containing zeros with uniform p values
        uniform_p = 1 / len(self.states)
        zero_row = np.argwhere(self.observed_p_matrix.sum(1) == 0).ravel()
        #self.observed_p_matrix[zero_row, :] = uniform_p
        # expected transition frequency matrix
        self.expected_matrix = ss.contingency.expected_freq(self.observed_matrix)

