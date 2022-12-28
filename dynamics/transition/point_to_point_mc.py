from dynamics.transition.second_level_mc import MarkovChainSecondLevel
import numpy as np
import scipy.stats as ss
from collections import OrderedDict
from dynamics.transition.intra_day_transition import DayFullStateGenerator
open_type_codes = ['GAP_UP',  'ABOVE_VA', 'INSIDE_VA', 'BELOW_VA', 'GAP_DOWN']

class MarkovChainPointToPoint(MarkovChainSecondLevel):
    def build_transition_model(self, data, transitions):
        """
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
            for idx in range(len(transition_list) - 1):
                state = transition_list[idx]
                follow = transition_list[idx + 1]
                model[features['open_type']][follow] += 1
                model[self.prev_state][follow] += 1
                if follow not in model[state]:
                    model[state][follow] = 0
                model[state][follow] += 1
                model[state]['count'] += 1

                """-- only for debug"""

                if state == 'D19' or follow == 'D19':
                    print(day, "=======================================================")
                    print(transition_list[0:idx + 2])
                    print(model[state])

        #print(dict(model))
        self.model = model


