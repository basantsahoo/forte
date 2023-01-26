from dynamics.constants import *
human_machine_signal_map = {
    'OPEN_TYPE': (PATTERN_STATE, STATE_OPEN_TYPE),
    'DT': (PRICE_ACTION_INTRA_DAY, INDICATOR_DOUBLE_TOP),
    'TREND': (PRICE_ACTION_INTRA_DAY, INDICATOR_TREND),
    'CANDLE_5_HIKKAKE_BUY': (CANDLE_5, 'CDLHIKKAKE_BUY'),
    'CANDLE_5_HIKKAKE_SELL': (CANDLE_5, 'CDLHIKKAKE_SELL'),
    'CANDLE_5_DOJI_SELL':(CANDLE_5, 'CDLDOJI_SELL'),
    'CANDLE_15_HIKKAKE_BUY': (CANDLE_15, 'CDLHIKKAKE_BUY'),
    'CANDLE_15_DOJI_SELL': (CANDLE_15, 'CDLDOJI_SELL'),
    'OPTION_PRICE_DROP': ('OPTION', 'PRICE_DROP'),
    'TECH_CDL_5_ABOVE_EMA_5': ('TECHNICAL', 'CDL_5_ABOVE_EMA_5'),
    'TECH_PRICE_BELOW_EMA_5': ('TECHNICAL', 'PRICE_BELOW_EMA_5'),
    'TECH_PRICE_ABOVE_EMA_5': ('TECHNICAL', 'PRICE_ABOVE_EMA_5')
}

human_machine_target_map = {
    'DT_HEIGHT_TARGET': {'category':'signal_queue', 'mapped_object': (PRICE_ACTION_INTRA_DAY, INDICATOR_DOUBLE_TOP), 'mapped_fn':'get_pattern_target', 'kwargs':{'ref_point':-2, 'factor':-1}},
    'PREV_SPH': {'category':'global', 'mapped_object': 'insight_book', 'mapped_fn':'get_prev_sph'},
    'PREV_SPL': {'category':'global', 'mapped_object': 'insight_book', 'mapped_fn':'get_prev_spl'},
    'LAST_N_CANDLE_BODY_TARGET_UP': {'category':'global', 'mapped_object': 'insight_book', 'mapped_fn':'get_n_candle_body_target_up', 'kwargs':{'period':5, 'n':3}},
    'LAST_N_CANDLE_BODY_TARGET_DOwN': {'category':'global', 'mapped_object': 'insight_book', 'mapped_fn':'get_n_candle_body_target_down', 'kwargs':{'period':5, 'n':3}},
    'LAST_N_CANDLE_HIGH': {'category': 'global', 'mapped_object': 'insight_book', 'mapped_fn': 'get_last_n_candle_high', 'kwargs': {'period': 5, 'n': 3}},
    'LAST_N_CANDLE_LOW': {'category':'global', 'mapped_object': 'insight_book', 'mapped_fn':'get_last_n_candle_low', 'kwargs':{'period':5, 'n':3}},
}


def get_signal_key(human_lang):
    if isinstance(human_lang, tuple):
        return human_lang
    else:
        return human_machine_signal_map.get(human_lang.upper(), None)


def get_target_fn(human_lang):
    return human_machine_target_map.get(human_lang.upper(), None)

def get_startegy_args(id=None, order_type='BUY', spot_instruments=[], derivative_instruments=[], exit_time=[30], min_tpo=1, max_tpo=13, record_metric=True, triggers_per_signal=1, max_signal=1, weekdays_allowed=[], entry_signal_queues=[], exit_criteria_list = [], signal_filters = [], spot_long_targets = [], spot_long_stop_losses = [], spot_short_targets=[], spot_short_stop_losses=[],  instr_targets = [], instr_stop_losses = [], instr_to_trade=[]):
    args = {}
    arg_list = ["id", "order_type", "spot_instruments", "derivative_instruments", "exit_time", "min_tpo", "max_tpo", "record_metric", "triggers_per_signal", "max_signal","weekdays_allowed","entry_signal_queues", "exit_criteria_list", "signal_filters", "spot_long_targets", "spot_long_stop_losses", "spot_short_targets", "spot_short_stop_losses", "instr_targets", "instr_stop_losses", "instr_to_trade"]
    for arg_ in arg_list:
        #if eval(arg_):
        args[arg_] = eval(arg_)
    return args


