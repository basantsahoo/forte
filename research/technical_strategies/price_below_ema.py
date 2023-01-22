from research.strategies.t_core_strategy  import BaseStrategy
from research.strategies.signal_setup import get_startegy_args, get_signal_key
from helper.utils import get_option_strike


class PriceBreakEMADownward(BaseStrategy):
    def __init__(self, insight_book, id="PriceBreakEMADownward", order_type='BUY', spot_instruments=[], derivative_instruments=[], exit_time=30, min_tpo=1, max_tpo=13, record_metric=True, triggers_per_signal=1, max_signal=1, weekdays_allowed=[],entry_criteria=[],exit_criteria_list=[],signal_filter_conditions=[],spot_long_targets=[],spot_long_stop_losses=[], spot_short_targets=[0.002,0.003, 0.004, 0.005], spot_short_stop_losses=[0.001,0.002, 0.002,0.002], instr_targets=[], instr_stop_losses=[]):
        args = get_startegy_args(id=id, order_type=order_type, spot_instruments=spot_instruments, derivative_instruments=derivative_instruments, exit_time=exit_time, min_tpo=min_tpo, max_tpo=max_tpo, record_metric=record_metric, triggers_per_signal=triggers_per_signal, max_signal=max_signal,weekdays_allowed=weekdays_allowed, entry_criteria=entry_criteria, exit_criteria_list=exit_criteria_list,signal_filter_conditions=signal_filter_conditions, spot_long_targets=spot_long_targets, spot_long_stop_losses=spot_long_stop_losses, spot_short_targets=spot_short_targets, spot_short_stop_losses=spot_short_stop_losses, instr_targets=instr_targets, instr_stop_losses=instr_stop_losses)
        args['entry_criteria'] = [
            {'TECH_CDL_5_ABOVE_EMA_5': []},
            {'TECH_PRICE_BELOW_EMA_5': [-1, 'strength', ">", 0]},
        ]
        exit_criteria_list = [[
            {'CANDLE_5_DOJI_SELL': [-1, 'time_lapsed', ">=", 5]}
        ]]
        BaseStrategy.__init__(self, insight_book=insight_book, **args)
        self.instr_to_trade = [["OTM", 1, "PE"]]


    def register_instrument(self, signal):
        if (signal['category'], signal['indicator']) == get_signal_key('TECH_PRICE_BELOW_EMA_5'):
            self.derivative_instruments = []
            last_tick = self.get_last_tick('SPOT')
            ltp = last_tick['close']
            for instr in self.instr_to_trade:
                strike = get_option_strike(ltp, instr[0], instr[1], instr[2])
                self.derivative_instruments.append(str(strike) + "_" + instr[2])

    def process_post_entry(self):
        self.derivative_instruments = []

