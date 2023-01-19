from research.strategies.t_core_strategy import BaseStrategy


class BaseOptionStrategy(BaseStrategy):
    def __init__(self,
                 insight_book=None,
                 id=None,
                 order_type="BUY",
                 spot_instruments=[],
                 derivative_instruments=[],
                 exit_time=10,
                 min_tpo=1,
                 max_tpo=13,
                 record_metric=True,
                 triggers_per_signal=1,
                 max_signal=1,
                 weekdays_allowed=[],
                 entry_criteria=[],
                 exit_criteria_list=[],
                 signal_filter_conditions=[],
                 spot_targets=[],
                 instr_targets=[],
                 spot_stop_losses = [],
                 instr_stop_losses = []

    ):
        print('BaseOptionStrategy init', derivative_instruments)
        BaseStrategy.__init__(self, insight_book, id, order_type,spot_instruments, derivative_instruments, exit_time, min_tpo, max_tpo, record_metric, triggers_per_signal,
                              max_signal, weekdays_allowed, entry_criteria,exit_criteria_list, signal_filter_conditions, spot_targets, instr_targets, spot_stop_losses, instr_stop_losses)

    def test_base(self):
        print('test base', self.derivative_instruments)