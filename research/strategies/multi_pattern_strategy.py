from research.core_strategies.t_core_strategy import BaseStrategy


class MultiPatternStrategy(BaseStrategy):
    def __init__(self, insight_book, id, order_type, spot_instruments, derivative_instruments, exit_time, min_tpo=1, max_tpo=13, record_metric=True, triggers_per_signal=1, max_signal=1, spot_short_targets=[0.002,0.003, 0.004, 0.005], spot_short_stop_losses=[0.001,0.002, 0.002,0.002], weekdays_allowed=[], signal_filter_conditions=[]):
        entry_criteria = [
            {'OPEN_TYPE': [-1, 'signal', "==", 'GAP_UP']},
            {'CANDLE_5_HIKKAKE_BUY': [-1, 'time_lapsed', "<=", 20]},
            {'CANDLE_5_HIKKAKE_BUY': [-1, 'time_lapsed', ">=", 5]},
            {'DT': [-1, 'pattern_height', ">=", -100]},
            {'TREND': [-1, "all_waves[-1]['dist']", ">=", -100]}
        ]
        exit_criteria_list = [[
            {'CANDLE_5_DOJI_SELL': [-1, 'time_lapsed', ">=", 5]}
        ]]
        BaseStrategy.__init__(self, insight_book=insight_book, id=id, order_type=order_type, spot_instruments=spot_instruments, derivative_instruments=derivative_instruments, exit_time=exit_time, min_tpo=min_tpo, max_tpo=max_tpo, record_metric=record_metric, triggers_per_signal=triggers_per_signal, max_signal=max_signal, spot_short_targets=spot_short_targets, spot_short_stop_losses=spot_short_stop_losses, weekdays_allowed=weekdays_allowed, signal_filter_conditions=signal_filter_conditions, entry_criteria=entry_criteria, exit_criteria_list=exit_criteria_list)
        self.id = self.__class__.__name__ + "_" + order_type + "_" + str(exit_time) if id is None else id

