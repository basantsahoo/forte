from transition.markov_chain import MarkovChain
import numpy as np
import scipy.stats as ss
from collections import OrderedDict
from transition.intra_day_transition import DayFullStateGenerator
open_type_codes = ['GAP_UP',  'ABOVE_VA', 'INSIDE_VA', 'BELOW_VA', 'GAP_DOWN']

#TODO = 1.matrix by tpo, 2. daily poc trasition matrix, 3. transition on weekly poc
#TODO = 4. Poissons distributions of gap/up gap down to determine regime
#TODO = most likely state given opening period(s)
#TODO = Conditioned on Static energy of first few candles, state transition maxtrix
#TODO = Regime transition test when probability matrix shifts

class MarkovChainSecondLevel(MarkovChain):
    def build_transition_model(self, data, transitions):
        """
        For every state
        BEGIN -> state  increase by 1
        OPEN_TYPE -> state increase by 1
        State  -> follow increase by 1
        All passed States  -> follow increase by 1
        (Above only once per day)
        """
        print('==============build_transition_model===============')
        last_day = list(data.keys())[-1]
        feature_generator = DayFullStateGenerator("NIFTY", last_day)
        intermediate_steps = list(feature_generator.price_bands.values())

        model = OrderedDict()
        model[self.prev_state] = {'count':0} #Begin
        for open_type_code in open_type_codes: # open types
            model[open_type_code] = {'count':0}
            model[self.prev_state][open_type_code] = 0
        if transitions == 'tpo_transitions_direction':
            for tpo in range(1,14):
                for step in intermediate_steps:
                    for mov in ['F', 'R']:
                        model[str(tpo) + "_" + step + "_" + mov] = {'count': 0}
                        model[self.prev_state][str(tpo) + "_" + step + "_" + mov] = 0
                        for open_type_code in open_type_codes:
                            model[open_type_code][str(tpo) + "_" + step + "_" + mov] = 0
        elif transitions == 'unique_transitions_fill_break' or transitions == 'observed_transitions': #Intermediate states
            for step in intermediate_steps:
                model[step] = {'count': 0}
                model[self.prev_state][step] = 0
                for open_type_code in open_type_codes:
                    model[open_type_code][step] = 0
        #print(dict(model))
        for (day, features) in data.items():
            """
            if day != '2022-01-25':
                continue
            """
            model[self.prev_state]['count'] += 1 #Confirmed that new day
            model[self.prev_state][features['open_type']] += 1 #Confirmed on open type
            model[features['open_type']]['count'] += 1

            transition_list = features[transitions]
            day_inter_trans = OrderedDict()
            visited_states = []
            for idx in range(len(transition_list) - 1):
                state = transition_list[idx]
                follow = transition_list[idx + 1]
                if state != follow:
                    """-- only for debug"""
                    """
                    if state == 'D18': #and follow == 'D9':
                        print(day, "=======================================================")
                        #print(visited_states)
                    """
                    if state not in visited_states: #Update BEGIN and Open type graph once a day for each state
                        model[features['open_type']][state] += 1
                        model[self.prev_state][state] += 1
                        model[state]['count'] += 1
                        visited_states.append(state)

                    if state not in day_inter_trans: #Got a new start state
                        day_inter_trans[state] = {} # store that it's visited on that day
                        #model[state]['count'] += 1  #Does n't work for last follow

                    for v_state in [x for x in visited_states if x != follow]:  #Update all preceeding states
                        if follow not in day_inter_trans[v_state]: # new transition found
                            day_inter_trans[v_state][follow] = 1
                            if follow not in model[v_state]:
                                model[v_state][follow] = 0
                            model[v_state][follow] += 1
                            """ -- only for debug
                            if v_state == 'D10' and follow == 'D9':
                                print(day,"=======================================================")
                                print(transition_list[0:idx+2])
                                print(model[v_state][follow])
                            """
                    if follow not in visited_states: #Got a new end state
                        model[features['open_type']][follow] += 1
                        model[self.prev_state][follow] += 1
                        model[follow]['count'] += 1
                        visited_states.append(follow)
                    """-- only for debug"""
                    """
                    if state == 'D18': #and follow == 'D9':
                        print(day, "=======================================================")
                        print(transition_list[0:idx + 2])
                        print(model[state])
                    """
        #print(dict(model))
        self.model = model

    def get_intermediate_states(self, start, end):
        #print('get_intermediate_states==', start, end)
        if start is None:
            return [end]
        else:
            state_seq = intermediate_steps
            tr_seq = state_seq[state_seq.index(start) + 1:state_seq.index(end) + 1]
            if not tr_seq:
                state_seq.reverse()
                tr_seq = state_seq[state_seq.index(start) + 1:state_seq.index(end) + 1]
            return tr_seq

    def calc_transition_freq(self):
        print('==============calc_transition_freq===============')
        self.states = np.array(list(self.model.keys()))
        self.observed_matrix = np.zeros((len(self.states), len(self.states)))
        self.observed_p_matrix = np.zeros((len(self.states), len(self.states)))
        self.total_matrix = np.zeros((len(self.states), len(self.states)))
        for x in range(len(self.states)):
            xid = np.argwhere(self.states == self.states[x]).flatten()
            transitions = self.model[self.states[x]]
            for to_state in list(transitions.keys()):
                yid = np.argwhere(self.states == to_state).flatten()
                cnt = transitions[to_state]
                self.observed_matrix[xid, yid] = cnt
                self.total_matrix[xid, yid] = transitions['count']
                #self.observed_matrix[xid, yid] = str(cnt) + "/" + str(transitions['count'])
                self.observed_p_matrix[xid, yid] = transitions['count'] and cnt/transitions['count'] or 0

        print('==============calc_transition_freq ends===============')

    def get_prob_from_curr_state(self, curr_state, fut_states=[]):
        ret_val = {}
        xid = np.argwhere(self.states == curr_state).flatten()
        if fut_states:
            for f_state in fut_states:
                yid = np.argwhere(self.states == f_state).flatten()
                ret_val[f_state] = self.observed_p_matrix[xid, yid]
        else:
            all_state_prob = self.observed_p_matrix[xid][0]
            ret_val = dict(zip(self.states, all_state_prob))
        return ret_val

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