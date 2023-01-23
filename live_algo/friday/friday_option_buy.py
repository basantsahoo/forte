from research.strategies.cheap_option_buy import CheapOptionBuy
from helper.utils import get_option_strike
from research.strategies.signal_setup import get_signal_key

class FridayOptionBuy(CheapOptionBuy):
    def __init__(self, insight_book, id="OPTION_CHEAP_BUY_FRI", exit_time=60, max_signal = 10, instr_targets=[0.1,0.2, 0.3, 0.5], instr_stop_losses=[0.5,0.5, 0.5,0.5]):
        CheapOptionBuy.__init__(self, insight_book, id=id,  exit_time=exit_time, max_signal=max_signal, instr_targets=instr_targets, instr_stop_losses=instr_stop_losses)
        self.weekdays_allowed = ['Friday']
        self.signal_filter_conditions = [{"op": "or", "logical_test": "category in [('OPTION','PRICE_DROP')] and open_type in ['GAP_UP'] and tpo in [1,2,6,7,8] and strength >= 20  and kind in ['PE'] and money_ness in ['ATM_0' , 'OTM_1' , 'OTM_2', 'OTM_3']"},
            {"op": "or", "logical_test": "category in [('OPTION','PRICE_DROP')] and open_type in ['ABOVE_VA'] and strength >= 20  and kind in ['CE'] and money_ness in ['ATM_0' , 'OTM_1' , 'OTM_2']"},
            {"op": "or", "logical_test": "category in [('OPTION','PRICE_DROP')] and open_type in ['ABOVE_VA'] and tpo in [2,3] and strength >= 20  and kind in ['PE'] and money_ness in ['OTM_3' , 'OTM_4', 'OTM_5']"},
            {"op": "or", "logical_test": "category in [('OPTION','PRICE_DROP')] and open_type in ['INSIDE_VA'] and tpo in [10,11] and strength >= 20  and kind in ['CE'] and money_ness in [ 'OTM_1' , 'OTM_2', 'OTM_3', 'OTM_4']"},
            {"op": "or", "logical_test": "category in [('OPTION','PRICE_DROP')] and open_type in ['GAP_DOWN'] and tpo in [1,6,7,8,9,10] and strength >= 20 and strength <= 30  and kind in ['CE'] and money_ness in ['OTM_1' , 'OTM_2', 'OTM_3']"}
        ]


class FridayBelowVA(CheapOptionBuy):
    def __init__(self, insight_book, id="BELOWVAFRI", exit_time=60,  max_signal = 2, instr_targets=[0.2, 0.3, 0.3, 0.5], instr_stop_losses=[0.25,0.3, 0.4,0.5]):
        CheapOptionBuy.__init__(self, insight_book, id=id,  exit_time=exit_time, max_signal=max_signal, instr_targets=instr_targets, instr_stop_losses=instr_stop_losses)
        self.weekdays_allowed = ['Friday']
        self.inst_to_trade = [["OTM", 1, "PE"]]
        self.put_bought = 0  # Do separate for this BELOW VA only buy Puts non of of them came below 20% in the sample
        self.signal_filter_conditions = [
            {"op": "or", "logical_test": "category in [('OPTION','PRICE_DROP')] and open_type in ['BELOW_VA'] and tpo in [1] "},
        ]

    def register_instrument(self, signal):
        if (signal['category'], signal['indicator']) == get_signal_key('OPTION_PRICE_DROP') and not self.put_bought:
            #print('instrument register')
            last_tick = self.get_last_tick('SPOT')
            ltp = last_tick['close']
            for instr in self.instr_to_trade:
                # e.g instr = ['OTM', 1, 'PE']
                strike = get_option_strike(ltp, instr[0], instr[1], instr[2])
                self.derivative_instruments.append(str(strike) + "_" + instr[2])
            self.put_bought = 1

    def process_post_entry(self):
        self.derivative_instruments = []
