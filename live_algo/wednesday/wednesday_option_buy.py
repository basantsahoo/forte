from research.strategies.cheap_option_buy import CheapOptionBuy

class WednesdayOptionBuy(CheapOptionBuy):
    def __init__(self, insight_book, id="OPTION_CHEAP_BUY_WED", exit_time=[30], min_tpo=1, max_tpo=13,  max_signal = 10, target_pct=[0.1,0.2, 0.3, 0.5], stop_loss_pct=[0.5,0.5, 0.5,0.5]):
        CheapOptionBuy.__init__(self, insight_book,id=id,  exit_time=exit_time, min_tpo=min_tpo, max_tpo=max_tpo, max_signal=max_signal, target_pct=target_pct, stop_loss_pct=stop_loss_pct)
        self.last_match = None
        self.weekdays_allowed = ['Wednesday']
        self.criteria = [
            {"op": "or", "logical_test": "open_type in ['GAP_UP'] and tpo in [1,2,3] and strength >= 30  and kind in ['PE'] and money_ness in ['ITM_1' , 'ATM_0' , 'OTM_1' , 'OTM_2' ]"},
            {"op": "or", "logical_test": "open_type in ['BELOW_VA'] and tpo in [1,2,3] and strength >= 30  and kind in ['PE'] and money_ness in ['OTM_1' , 'OTM_2' , 'OTM_3','OTM_4','OTM_5']"},
            {"op": "or", "logical_test": "open_type in ['BELOW_VA'] and tpo in [11] and strength >= 50  and kind in ['PE'] and money_ness in ['OTM_1' , 'OTM_2' , 'OTM_3','OTM_4','OTM_5']"},
            {"op": "or", "logical_test": "open_type in ['ABOVE_VA'] and tpo in [1,2,3,4,5, 9, 10] and strength >= 20  and kind in ['PE'] and money_ness in ['ATM_0' , 'OTM_1' , 'OTM_2' , 'OTM_3','OTM_4','OTM_5']"},
            {"op": "or", "logical_test": "open_type in ['GAP_DOWN'] and tpo in [1,2,3] and strength in [20,30]  and kind in ['PE'] and money_ness in ['ITM_2', 'ITM_3' ,'OTM_5']"},
            {"op": "or", "logical_test": "open_type in ['GAP_DOWN'] and tpo in [9,10,11] and strength >=50  and kind in ['PE'] and money_ness in ['OTM_1' , 'OTM_2' , 'OTM_3','OTM_4','OTM_5']"},
            {"op": "or", "logical_test": "open_type in ['ABOVE_VA'] and tpo in [1,2,10,11] and strength >=20  and kind in ['CE'] and money_ness in ['ITM_1' , 'ATM_0' , 'OTM_1' , 'OTM_2' ]"},
            {"op": "or", "logical_test": "open_type in ['BELOW_VA'] and tpo in [1,2,3] and strength >= 30  and kind in ['CE'] and money_ness in ['OTM_1' , 'OTM_2' , 'OTM_3','OTM_4','OTM_5']"},
            {"op": "or",  "logical_test": "open_type in ['BELOW_VA'] and tpo in [7,8,9] and strength >= 30  and kind in ['CE'] and money_ness in ['OTM_1' , 'OTM_2' , 'OTM_3','OTM_4','OTM_5']"},
            {"op": "or", "logical_test": "open_type in ['GAP_UP'] and tpo in [1] and strength >= 20  and kind in ['CE'] and money_ness in ['OTM_1' , 'OTM_2' , 'OTM_3','OTM_4','OTM_5']"},
            {"op": "or", "logical_test": "open_type in ['GAP_DOWN'] and tpo in [1,2,3,4,5,6,7] and strength >= 30  and kind in ['CE'] and money_ness in ['OTM_1' , 'OTM_2' , 'OTM_3','OTM_4','OTM_5']"},
            #{"op": "or",  "logical_test": "open_type in ['INSIDE_VA'] and tpo in [7,8,9,10,11] and strength >= 30  and kind in ['PE'] and money_ness in ['OTM_1' , 'OTM_2' , 'OTM_3','ITM_1','ITM_2']"}
        ]
        print('WednesdayOptionBuy init')

    def evaluate_signal(self, matched_pattern):
        print('process_pattern_signal wednesday+++++++++++', matched_pattern)
        last_match_ol = 0
        signal_passed = False
        """
        Control when a signal is considered for trade
        """
        #print("self.suitable_market_condition======", self.suitable_market_condition(matched_pattern))
        if not last_match_ol and self.suitable_market_condition(matched_pattern):
            self.last_match = matched_pattern
            print('in evaluate_signal,', self.record_metric)
            matched_pattern['candle'] = [0,0,0,0]
            self.record_params(matched_pattern)
            signal_passed = True
        #print('signal_passed====', signal_passed)
        return signal_passed
