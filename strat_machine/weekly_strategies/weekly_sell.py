from strat_machine.core_strategies.weekly_core_strategy  import BaseStrategy
from strat_machine.strategies.signal_setup import get_startegy_args
from helper.utils import get_option_strike


class WeeklySell(BaseStrategy):
    #def __init__(self, insight_book, id="PriceBreakEMADownward", order_type='BUY', spot_instruments=[], derivative_instruments=[], exit_time=[45], min_tpo=1, max_tpo=13, record_metric=True, triggers_per_signal=1, max_signal=1, weekdays_allowed=[],entry_criteria=[],exit_criteria_list=[],signal_filter_conditions=[],spot_long_targets=[],spot_long_stop_losses=[], spot_short_targets=[0.002,0.003, 0.004, 0.005], spot_short_stop_losses=[0.001,0.002, 0.002,0.002], instr_targets=[], instr_stop_losses=[]):
    def __init__(self, insight_book, **kwargs):
        print('WeeklySell+++++++++++++ init')
        args = get_startegy_args(**kwargs)
        BaseStrategy.__init__(self, insight_book=insight_book, **args)
        self.cover = 200

    def register_instrument(self, signal):
        if (signal['category'], signal['indicator']): #== get_signal_key('TECH_PRICE_BELOW_EMA_5'):
            self.derivative_instruments = []
            last_tick = self.get_last_tick('SPOT')
            ltp = last_tick['close']
            for instr in self.instr_to_trade:
                strike = get_option_strike(ltp, instr[0], instr[1], instr[2])
                self.derivative_instruments.append(str(strike) + "_" + instr[2])
        print('register instr', self.derivative_instruments)

    def process_post_entry(self):
        self.derivative_instruments = []

