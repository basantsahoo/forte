import numpy as np
from datetime import datetime
import helper.utils as helper_utils
from dynamics.trend.technical_patterns import pattern_engine
from statistics import mean
import dynamics.patterns.utils as pattern_utils
from helper.utils import get_broker_order_type
from research.strategies.core_strategy import BaseStrategy

class BaseOptionStrategy(BaseStrategy):
    def __init__(self,
                 insight_book=None,
                 id=None,
                 pattern=None,
                 order_type="BUY",
                 exit_time=10,
                 period=5,
                 trend=None,
                 min_tpo=1,
                 max_tpo=13,
                 record_metric=True,
                 triggers_per_signal=1,
                 max_signal=1,
                 target_pct = [0.2,0.3, 0.4, 0.5],
                 stop_loss_pct = [0.1,0.2, 0.3,0.4],
                 weekdays_allowed=[],
                 criteria=[]
                 ):
        BaseStrategy.__init__(self,insight_book,id,pattern,order_type,exit_time,period,trend,min_tpo,max_tpo,record_metric,triggers_per_signal,
                              max_signal,target_pct,stop_loss_pct,weekdays_allowed,criteria)

    def get_trades(self, pattern_info, idx=1, neck_point=0):
        instrument = pattern_info['instrument']
        last_candle = self.insight_book.option_processor.get_last_tick(instrument)
        close_point = last_candle['close']
        side = get_broker_order_type(self.order_type)
        neck_point = 0
        return {'seq': idx, 'instrument': instrument, 'target': close_point * (1 + side * self.target_pct[idx-1]), 'stop_loss':close_point * (1 - side * self.stop_loss_pct[idx-1]),'duration': self.exit_time, 'quantity': self.minimum_quantity, 'exit_type':None, 'entry_price':last_candle['close'], 'exit_price':None, 'neck_point': neck_point, 'trigger_time':pattern_info['time']}

    def trigger_entry(self, order_type, sig_key, triggers):
        #print('trigger_entry',triggers)
        #print(sig_key, order_type)
        #print(triggers)
        for trigger in triggers:
            if self.record_metric:
                mkt_parms = self.insight_book.activity_log.get_market_params()
                if self.signal_params:
                    mkt_parms = {**mkt_parms, **self.signal_params}
                self.params_repo[(sig_key, trigger['seq'])] = mkt_parms  # We are interested in signal features, trade features being stored separately
        updated_symbol = self.insight_book.ticker + "_" + triggers[0]['instrument']
        signal_info = {'symbol': updated_symbol, 'strategy_id': self.id, 'signal_id': sig_key, 'order_type': order_type, 'triggers': [{'seq': trigger['seq'], 'qty': trigger['quantity']} for trigger in triggers]}
        self.confirm_trigger(sig_key, triggers)
        self.insight_book.pm.strategy_entry_signal(signal_info, option_signal=True)

    def trigger_exit(self, signal_id, trigger_id, exit_type=None):
        #print('trigger_exit+++++++++++++++++++++++++++++', signal_id, trigger_id, exit_type)
        quantity = self.tradable_signals[signal_id]['triggers'][trigger_id]['quantity']
        instrument = self.tradable_signals[signal_id]['triggers'][trigger_id]['instrument']
        last_candle = self.insight_book.option_processor.get_last_tick(instrument)
        updated_symbol = self.insight_book.ticker + "_" + instrument
        signal_info = {'symbol': updated_symbol, 'strategy_id': self.id, 'signal_id': signal_id,
                       'trigger_id': trigger_id,
                       'qty': quantity}

        self.tradable_signals[signal_id]['triggers'][trigger_id]['closed'] = True
        self.tradable_signals[signal_id]['triggers'][trigger_id]['exit_type'] = exit_type
        self.tradable_signals[signal_id]['triggers'][trigger_id]['exit_price'] = last_candle['close']
        self.insight_book.pm.strategy_exit_signal(signal_info, option_signal=True)

    def trigger_exit_at_low(self, signal_id, trigger_id):
        lowest_candle = self.insight_book.option_processor.get_lowest_candle()
        self.insight_book.pm.strategy_exit_signal(self.insight_book.ticker, self.id, signal_id, trigger_id, lowest_candle)

    def add_new_signal_to_journal(self, pattern_match_idx):
        existing_signals = len(self.tradable_signals.keys())
        sig_key = 'SIG_' + str(existing_signals + 1)
        self.tradable_signals[sig_key] = {}
        #self.tradable_signals[sig_key]['instrument'] = pattern_match_idx['instrument']
        self.tradable_signals[sig_key]['triggers'] = {}
        self.tradable_signals[sig_key]['targets'] = []
        self.tradable_signals[sig_key]['stop_losses'] = []
        self.tradable_signals[sig_key]['time_based_exists'] = []
        self.tradable_signals[sig_key]['trade_completed'] = False
        self.tradable_signals[sig_key]['pattern'] = pattern_match_idx
        self.tradable_signals[sig_key]['pattern_height'] = 0
        self.tradable_signals[sig_key]['max_triggers'] = self.triggers_per_signal
        return sig_key

    """
    Define custom strategy parameters here
    add_tradable_signal gives stretegies to define their own parameters to be added signals for record keeping
    """
    def add_tradable_signal(self, pattern_match_idx):
        sig_key = self.add_new_signal_to_journal(pattern_match_idx)
        return sig_key

    def confirm_trigger(self, sig_key, triggers):
        curr_signal = self.tradable_signals[sig_key]
        for trigger in triggers:
            curr_signal['targets'].append(trigger['target'])
            curr_signal['stop_losses'].append(trigger['stop_loss'])
            curr_signal['time_based_exists'].append(trigger['duration'])
            curr_signal['triggers'][trigger['seq']] = trigger

    def initiate_signal_trades(self, sig_key):
        #print('initiate_signal_trades+++++', sig_key)
        curr_signal = self.tradable_signals[sig_key]
        next_trigger = len(curr_signal['triggers']) + 1
        triggers = [self.get_trades(curr_signal['pattern'], trd_idx) for trd_idx in range(next_trigger, next_trigger+self.triggers_per_signal)]
        # At first signal we will add 2 positions with target 1 and target 2 with sl mentioned above
        #total_quantity = sum([trig['quantity'] for trig in triggers])
        self.trigger_entry(self.order_type, sig_key, triggers)

    def process_signal(self, pattern, pattern_match_idx):
        if self.relevant_signal(pattern, pattern_match_idx) and (len(self.tradable_signals.keys()) < self.max_signal):
            #print('process_signal in core++++++++++++++++++++++++++', self.id, "tpo====", self.insight_book.curr_tpo, "minutes past===", len(self.insight_book.market_data.items()), "last tick===" , self.insight_book.last_tick['timestamp'])
            signal_passed = self.evaluate_signal(pattern_match_idx) #len(self.tradable_signals.keys()) < self.max_signals+5  #
            if signal_passed:
                sig_key = self.add_tradable_signal(pattern_match_idx)
                self.initiate_signal_trades(sig_key)

    def monitor_sell_positions(self):
        #print(self.tradable_signals)
        for signal_id, signal in self.tradable_signals.items():
            #print(signal)
            for trigger_seq, trigger_details in signal['triggers'].items():
                last_candle = self.insight_book.option_processor.get_last_tick(trigger_details['instrument'])
                if trigger_details['exit_type'] is None:  #Still active
                    #print(trigger_details)
                    if last_candle['close'] < trigger_details['target']:
                        self.trigger_exit(signal_id, trigger_seq, exit_type=1)
                        #print(last_candle, trigger_details['target'])
                    elif last_candle['close'] >= trigger_details['stop_loss']:
                        self.trigger_exit(signal_id, trigger_seq, exit_type=-1)
                    elif last_candle['timestamp'] - trigger_details['trigger_time'] >= trigger_details['duration']*60:
                        self.trigger_exit(signal_id, trigger_seq, exit_type=0)

    def monitor_buy_positions(self):
        #print(self.tradable_signals)
        for signal_id, signal in self.tradable_signals.items():
            #print(signal)
            for trigger_seq, trigger_details in signal['triggers'].items():
                last_candle = self.insight_book.option_processor.get_last_tick(trigger_details['instrument'])
                if trigger_details['exit_type'] is None:  #Still active
                    #print(trigger_details)
                    if last_candle['close'] >= trigger_details['target']:
                        self.trigger_exit(signal_id, trigger_seq, exit_type=1)
                        #print(last_candle, trigger_details['target'])
                    elif last_candle['close'] < trigger_details['stop_loss']:
                        self.trigger_exit(signal_id, trigger_seq, exit_type=-1)
                    elif last_candle['timestamp'] - trigger_details['trigger_time'] >= trigger_details['duration']*60:
                        self.trigger_exit(signal_id, trigger_seq, exit_type=0)
