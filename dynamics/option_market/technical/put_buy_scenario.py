import numpy as np
from entities.base import Signal
from pathlib import Path
import json

signal_config_path = str(Path(__file__).resolve().parent.parent.parent.parent) + "/live_algo/" + 'signal_parameters.json'
with open(signal_config_path, 'r') as sig_cong:
    signal_config = json.load(sig_cong)


class PutBuyScenario:
    def __init__(self, info_fn=None, call_back_fn=None):
        self.call_back_fn = call_back_fn
        self.info_fn = info_fn
        self.last_signal_idx = 0

    def evaluate(self):
        info = self.info_fn()
        for scenario in signal_config['option_signals']:
            scenarion_met = True
            for param, range in scenario['criteria'].items():
                param_val = info[param]
                criterion_met = (param_val >= range['min']) and (param_val <= range['max'])
                scenarion_met = scenarion_met and criterion_met

            if scenarion_met:
                #print('dispatch signal+++++++++', scenario['name'])
                signal = Signal(asset=info['asset'], category='OPTION_MARKET', instrument="OPTION",
                                indicator=scenario['name'], strength=1, signal_time=info['timestamp'],
                                notice_time=info['timestamp'], info=info)
                self.call_back_fn(signal)
