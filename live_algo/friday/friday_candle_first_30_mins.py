from research.core_strategies.t_core_strategy import BaseStrategy
from research.strategies.signal_setup import get_signal_key
from helper.utils import get_option_strike


class FridayCandleFirst30Buy(BaseStrategy):
    def __init__(self,
                 insight_book=None,
                 id=None,
                 order_type="BUY",
                 spot_instruments=[],
                 derivative_instruments=[],
                 exit_time=30,
                 min_tpo=1,
                 max_tpo=13,
                 record_metric=True,
                 triggers_per_signal=1,
                 max_signal=1,
                 weekdays_allowed=[],
                 entry_criteria=[],
                 exit_criteria_list=[],
                 signal_filter_conditions=[],
                 spot_long_targets=[0.002,0.003, 0.004, 0.005],
                 spot_long_stop_losses=[0.001, 0.002, 0.002,0.002],
                 spot_short_targets=[],
                 spot_short_stop_losses=[],
                 instr_targets=[0.1,0.2, 0.3, 0.5],
                 instr_stop_losses=[0.5, 0.5, 0.5, 0.5]

                 ):
        entry_criteria = [{'CANDLE_5_HIKKAKE_BUY': []}]
        BaseStrategy.__init__(self,
                              insight_book=insight_book,
                              id=id,
                              order_type=order_type,
                              spot_instruments=spot_instruments,
                              derivative_instruments=derivative_instruments,
                              exit_time=exit_time,
                              min_tpo=min_tpo,
                              max_tpo=max_tpo,
                              record_metric=record_metric,
                              triggers_per_signal=triggers_per_signal,
                              max_signal=max_signal,
                              weekdays_allowed=weekdays_allowed,
                              entry_criteria=entry_criteria,
                              exit_criteria_list=exit_criteria_list,
                              signal_filter_conditions=signal_filter_conditions,
                              spot_long_targets=spot_long_targets,
                              spot_long_stop_losses=spot_long_stop_losses,
                              spot_short_targets=spot_short_targets,
                              spot_short_stop_losses=spot_short_stop_losses,
                              instr_targets=instr_targets,
                              instr_stop_losses=instr_stop_losses)
        self.weekdays_allowed = ['Friday']
        self.instr_to_trade = [["OTM", 1, "CE"]]

    def suitable_market_condition(self):
        return super().suitable_market_condition() and self.insight_book.get_time_since_market_open() <= 30

    def register_instrument(self, signal):
        if (signal['category'], signal['indicator']) == get_signal_key('CANDLE_5_HIKKAKE_BUY'):
            last_tick = self.get_last_tick('SPOT')
            ltp = last_tick['close']
            for instr in self.instr_to_trade:
                strike = get_option_strike(ltp, instr[0],instr[1], instr[2])
                self.derivative_instruments.append(str(strike) + "_" + instr[2])

    def process_post_entry(self):
        self.derivative_instruments = []



class FridayCandleFirst30Sell(BaseStrategy):
    def __init__(self,
                 insight_book=None,
                 id=None,
                 order_type="BUY",
                 spot_instruments=[],
                 derivative_instruments=[],
                 exit_time=30,
                 min_tpo=1,
                 max_tpo=13,
                 record_metric=True,
                 triggers_per_signal=1,
                 max_signal=1,
                 weekdays_allowed=[],
                 entry_criteria=[],
                 exit_criteria_list=[],
                 signal_filter_conditions=[],
                 spot_long_targets=[],
                 spot_long_stop_losses=[],
                 spot_short_targets=[0.002, 0.003, 0.004, 0.005],
                 spot_short_stop_losses=[0.001, 0.002, 0.002, 0.002],
                 instr_targets=[0.1, 0.2, 0.3, 0.5],
                 instr_stop_losses=[0.5, 0.5, 0.5, 0.5]
                 ):
        entry_criteria = [{'CANDLE_5_HIKKAKE_SELL': []}]
        BaseStrategy.__init__(self,
                              insight_book=insight_book,
                              id=id,
                              order_type=order_type,
                              spot_instruments=spot_instruments,
                              derivative_instruments=derivative_instruments,
                              exit_time=exit_time,
                              min_tpo=min_tpo,
                              max_tpo=max_tpo,
                              record_metric=record_metric,
                              triggers_per_signal=triggers_per_signal,
                              max_signal=max_signal,
                              weekdays_allowed=weekdays_allowed,
                              entry_criteria=entry_criteria,
                              exit_criteria_list=exit_criteria_list,
                              signal_filter_conditions=signal_filter_conditions,
                              spot_long_targets=spot_long_targets,
                              spot_long_stop_losses=spot_long_stop_losses,
                              spot_short_targets=spot_short_targets,
                              spot_short_stop_losses=spot_short_stop_losses,
                              instr_targets=instr_targets,
                              instr_stop_losses=instr_stop_losses)
        self.weekdays_allowed = ['Friday']
        self.instr_to_trade = [["OTM", 1, "PE"]]

    def suitable_market_condition(self):
        return super().suitable_market_condition() and self.insight_book.get_time_since_market_open() <= 30

    def register_instrument(self, signal):
        if (signal['category'], signal['indicator']) == get_signal_key('CANDLE_5_HIKKAKE_SELL'):
            last_tick = self.get_last_tick('SPOT')
            ltp = last_tick['close']
            for instr in self.instr_to_trade:
                strike = get_option_strike(ltp, instr[0], instr[1], instr[2])
                self.derivative_instruments.append(str(strike) + "_" + instr[2])

    def process_post_entry(self):
        self.derivative_instruments = []

