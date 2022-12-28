from db.market_data import (get_nth_day_profile_data, get_hist_ndays_profile_data)
from dynamics import profile as profile_utils
from itertools import chain, product
import calendar
import talib
import numpy as np
from collections import OrderedDict
from dynamics.transition.intra_day_transition import DayFullStateGenerator

class MCPreprocessor:
    def get_processed_data(self, data, symbol="NIFTY",feature_generator=None, start_tpo=None, end_tpo=None, use_range=[]):
        last_day = list(data.keys())[-1]
        if feature_generator is None:
            feature_generator = DayFullStateGenerator(symbol, last_day)
        self.price_bands = feature_generator.price_bands
        if start_tpo is None:
            start_tpo = 1

        for (day, features) in data.items():
            if not use_range:
                period_end = len(features['observed_transitions']) if end_tpo is None else end_tpo * 30
                period = range((start_tpo - 1) * 30, period_end)
            else:
                period = use_range
            features['observed_transitions'] = [features['observed_transitions'][x] for x in period]
            features['tpo_transitions_direction'] = self.get_tpo_transitions_with_direction(features['observed_transitions'])
            features['unique_transitions_fill_break'] = self.get_unique_transitions_fill_break(features['observed_transitions'])
        return data

    def get_intermediate_states(self, start, end):
        #print('get_intermediate_states==', start, end)
        if start is None:
            return [end]
        else:
            state_seq = list(self.price_bands.values())
            tr_seq = state_seq[state_seq.index(start) + 1:state_seq.index(end) + 1]
            if not tr_seq:
                state_seq.reverse()
                tr_seq = state_seq[state_seq.index(start) + 1:state_seq.index(end) + 1]
            return tr_seq

    def get_tpo_transitions_with_direction(self, transition_list):
        def move_direction(c_state, t_list, state_seq):
            direction = 'F'
            states_before = state_seq[0:state_seq.index(c_state)]
            states_after = state_seq[state_seq.index(c_state) + 1:]
            count_states_before = len(set(states_before).intersection(set(t_list)))
            count_states_after = len(set(states_after).intersection(set(t_list)))
            if count_states_before and count_states_after:
                direction = 'R'
            return direction

        state_seq = list(self.price_bands.values())
        tmp_transition_list = []
        refined_transition_list = []
        curr_tpo = 0
        last_state = None
        for state in transition_list:
            #print('+++++++++++++' + state + '+++++++++++++++++++')
            cat = move_direction(state, tmp_transition_list, state_seq)
            #print(cat)
            if len(tmp_transition_list) % 30 == 0:
                curr_tpo += 1
            if last_state != state:
                transited_states = self.get_intermediate_states(last_state, state)
                #print(transited_states)
                for t_state in transited_states:
                    refined_transition_list.append(str(curr_tpo) + "_" + t_state + "_" + cat)
                #print(refined_transition_list)
                last_state = state
            tmp_transition_list.append(state)
        return refined_transition_list

    def get_unique_transitions_fill_break(self, transition_list):
        refined_transition_list = []
        last_state = None
        for state in transition_list:
            if last_state != state:
                transited_states = self.get_intermediate_states(last_state, state)
                #print(transited_states)
                for t_state in transited_states:
                    refined_transition_list.append(t_state)
                #print(refined_transition_list)
                last_state = state
        return refined_transition_list
