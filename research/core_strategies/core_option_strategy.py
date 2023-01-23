from research.core_strategies.t_core_strategy import BaseStrategy


class BaseOptionStrategy(BaseStrategy):
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
                 spot_short_targets=[],
                 spot_short_stop_losses=[],
                 instr_targets=[],
                 instr_stop_losses = []

    ):
        print('BaseOptionStrategy init', derivative_instruments)
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

    def test_base(self):
        print('test base', self.derivative_instruments)