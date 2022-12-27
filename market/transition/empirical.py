import numpy as np
import scipy.stats as ss
from collections import OrderedDict
from copy import deepcopy


class EmpiricalDistribution:
    def __init__(self,data,transition_field="transitions"):
        self.data = data
        self.transition_field = transition_field

    def get_filtered_data(self, curr_events):
        data = deepcopy(self.data)
        for event in curr_events:
            if event['type'] == 'open_type':
                data = {k: v for (k, v) in data.items() if v['open_type'] == event['value']}
            if event['type'] == 'state':
                data = {k: v for (k, v) in data.items() if event['value'] in v[self.transition_field]}
        return data


    def get_distribution(self, curr_events=[], forecast_states=[]):
        sample_space = self.get_filtered_data(curr_events)
        #print(sample_space)
        passed_states = set([event['value'] for event in curr_events if event['type'] == 'state'])
        print('passed_states', passed_states)
        count_uni_set = len(list(self.data.keys()))
        count_sample_space = len(list(sample_space.keys()))
        result = {}
        for f_state in forecast_states:
            u_positive_outcomes = 0
            c_positive_outcomes = 0
            for (day, features) in sample_space.items():
                transition_list = features[self.transition_field]
                if f_state in transition_list:
                    #print(day)
                    last_index = max(i for i, v in enumerate(transition_list) if v == f_state)
                    states_before = set(transition_list[0:last_index])
                    #print(transition_list)
                    #print(transition_list[0:last_index+1])
                    if passed_states.issubset(states_before):
                        c_positive_outcomes += 1

            for (day, features) in self.data.items():
                transition_list = features[self.transition_field]
                if f_state in transition_list:
                    u_positive_outcomes += 1

            result[f_state] = {'count_uni_set': count_uni_set, 'u_positive_outcomes':u_positive_outcomes, 'count_sample_space': count_sample_space, 'c_positive_outcomes': c_positive_outcomes}
        return result