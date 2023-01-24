from research.core_strategies.pipe_strategy import PipeStrategy
from research.queues.q_network import QNetwork

class MultiPatternQueueStrategy(PipeStrategy):
    def __init__(self, insight_book, **kwargs):
        entry_signal_queues = [
            {'signal_type':'OPEN_TYPE','eval_criteria': [-1, 'signal', "==", 'GAP_UP'], 'flush_hist':True, 'id':0, 'dependent_on':[]},
            {'signal_type': 'CANDLE_5_HIKKAKE_BUY', 'eval_criteria': [-1, 'time_lapsed', "<=", 20], 'flush_hist':True, 'id': 1, 'dependent_on': [0]},
            {'signal_type': 'CANDLE_5_HIKKAKE_BUY', 'eval_criteria': [-1, 'time_lapsed', "<=", 20], 'flush_hist':True, 'id': 2,
             'dependent_on': [0]},
            {'signal_type': 'DT', 'eval_criteria': [-1, 'pattern_height', ">=", -100], 'flush_hist':True, 'id': 3,
             'dependent_on': [0]},
            {'signal_type': 'TREND', 'eval_criteria': [-1, "all_waves[-1]['dist']", ">=", -100], 'flush_hist':True, 'id': 4,
             'dependent_on': [0]}
        ]
        exit_criteria_list = [{'signal_type':'CANDLE_5_DOJI_SELL','eval_criteria': [-1, 'time_lapsed', ">=", 5], 'flush_hist':True, 'id':0, 'dependent_on':[]}],
        """
        exit_criteria_list = [[
            {'CANDLE_5_DOJI_SELL': [-1, 'time_lapsed', ">=", 5]}
        ]]
        """
        kwargs['exit_criteria_list'] = exit_criteria_list
        PipeStrategy.__init__(self, insight_book, **kwargs)
        self.signal_pipeline = QNetwork(self, entry_signal_queues)
