from research.strategies.cheap_option_buy import CheapOptionBuy


class TuesdayOptionBuy(CheapOptionBuy):
    def __init__(self, insight_book, id="OPTION_CHEAP_BUY_TUE", exit_time=60, max_signal = 10, instr_targets=[0.1,0.2, 0.3, 0.5], instr_stop_losses=[0.5,0.5, 0.5,0.5]):
        CheapOptionBuy.__init__(self, insight_book, id=id,  exit_time=exit_time, max_signal=max_signal, instr_targets=instr_targets, instr_stop_losses=instr_stop_losses)
        self.weekdays_allowed = ['Friday']
        self.signal_filter_conditions = [
            {"op": "or", "logical_test": "category in [('OPTION','PRICE_DROP')] and open_type in ['GAP_UP'] and tpo in [1] and strength >= 20 and strength <= 30  and kind in ['CE'] and money_ness in ['OTM_1' , 'OTM_2']"},
            {"op": "or", "logical_test": "category in [('OPTION','PRICE_DROP')] and open_type in ['GAP_UP'] and tpo in [5] and strength >= 50  and kind in ['CE'] and money_ness in ['OTM_1']"},
            {"op": "or", "logical_test": "category in [('OPTION','PRICE_DROP')] and open_type in ['GAP_UP'] and tpo in [8] and strength >= 30  and kind in ['CE'] and money_ness in ['OTM_4', 'OTM_5']"},
            {"op": "or", "logical_test": "category in [('OPTION','PRICE_DROP')] and open_type in ['GAP_UP'] and tpo in [9] and strength >= 60  and kind in ['CE'] and money_ness in ['OTM_2']"},
            {"op": "or", "logical_test": "category in [('OPTION','PRICE_DROP')] and open_type in ['GAP_UP'] and tpo in [11] and strength >= 40  and kind in ['CE'] and money_ness in ['OTM_5']"},
            {"op": "or", "logical_test": "category in [('OPTION','PRICE_DROP')] and open_type in ['INSIDE_VA'] and tpo in [3, 4, 5, 6, 9] and strength >= 30  and kind in ['CE'] and money_ness in ['ATM_0', 'OTM_1']"},

            {"op": "or", "logical_test": "category in [('OPTION','PRICE_DROP')] and open_type in ['GAP_UP'] and tpo in [3] and strength >= 40  and kind in ['PE'] and money_ness in ['OTM_2']"},
            {"op": "or",  "logical_test": "category in [('OPTION','PRICE_DROP')] and open_type in ['GAP_UP'] and tpo in [10, 11] and strength >= 30  and kind in ['PE'] and money_ness in ['OTM_3']"},
            {"op": "or", "logical_test": "category in [('OPTION','PRICE_DROP')] and open_type in ['INSIDE_VA'] and tpo in [1] and strength >= 20  and kind in ['PE'] and money_ness in ['ITM_1']"},
            {"op": "or", "logical_test": "category in [('OPTION','PRICE_DROP')] and open_type in ['INSIDE_VA'] and tpo in [9,10] and strength >= 20  and kind in ['PE'] and money_ness in ['OTM_4']"},

        ]

# Notes : Tuesday inside VA not good for selling
class TuesdayOptionSell(CheapOptionBuy):
    def __init__(self, insight_book, id="OPTION_CHEAP_BUY_TUE", exit_time=60, max_signal = 10, instr_targets=[0.1,0.2, 0.3, 0.5], instr_stop_losses=[0.5,0.5, 0.5,0.5]):
        CheapOptionBuy.__init__(self, insight_book, id=id,  exit_time=exit_time, max_signal=max_signal, instr_targets=instr_targets, instr_stop_losses=instr_stop_losses)
        self.weekdays_allowed = ['Friday']
        self.signal_filter_conditions = [
            {"op": "or", "logical_test": "category in [('OPTION','PRICE_DROP')] and open_type in ['GAP_UP'] and tpo in [2] and strength >= 20 and strength <= 30  and kind in ['CE'] and money_ness in ['OTM_1' , 'OTM_2']"},
            {"op": "or", "logical_test": "category in [('OPTION','PRICE_DROP')] and open_type in ['GAP_UP'] and tpo in [3] and strength >= 20 and strength <= 30  and kind in ['CE'] and money_ness in ['ITM_1' , 'ATM_0' , 'OTM_1', 'OTM_2']"},
            {"op": "or", "logical_test": "category in [('OPTION','PRICE_DROP')] and open_type in ['GAP_UP'] and tpo in [10] and strength >= 30   and kind in ['CE'] and money_ness in ['ITM_1']"},
            #PE
            {"op": "or", "logical_test": "category in [('OPTION','PRICE_DROP')] and open_type in ['GAP_UP'] and tpo in [1] and strength >= 20   and kind in ['PE'] and money_ness in ['ATM_0' , 'OTM_1', 'OTM_2']"},
            {"op": "or", "logical_test": "category in [('OPTION','PRICE_DROP')] and open_type in ['GAP_UP'] and tpo in [6] and strength >= 40   and kind in ['PE'] and money_ness in ['OTM_1']"},
        ]
