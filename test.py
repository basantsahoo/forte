from research.queues.neuron_network import QNetwork
from research.queues.neurons import Neuron
import json
strat_config_file = '/Users/basant/Work/PNL/forte/backtest/scenarios/ema_act_2_tick_watcher_redesign.json'

with open(strat_config_file) as bt_config:
    strat_config = json.load(bt_config)
    #print(strat_config['entry_signal_queues'])

network = QNetwork(None, strat_config['strategy_kwargs'][0]['entry_signal_queues'])
