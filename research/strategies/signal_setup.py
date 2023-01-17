from dynamics.constants import *
human_machine_signal_map = {
    'OPEN_TYPE': (PATTERN_STATE, STATE_OPEN_TYPE),
    'DT': (PRICE_ACTION_INTRA_DAY, INDICATOR_DOUBLE_TOP),
    'TREND': (PRICE_ACTION_INTRA_DAY, INDICATOR_TREND),
    'CANDLE_5_HIKKAKE_BUY': (CANDLE_5, 'CDLHIKKAKE_BUY'),
    'CANDLE_5_DOJI_SELL':(CANDLE_5, 'CDLDOJI_SELL'),
    'CANDLE_15_HIKKAKE_BUY': (CANDLE_15, 'CDLHIKKAKE_BUY'),
    'CANDLE_15_DOJI_SELL': (CANDLE_15, 'CDLDOJI_SELL'),
    'OPTION_PRICE_DROP': ('OPTION', 'PRICE_DROP')
}

human_machine_target_map = {
    'DT_HEIGHT_TARGET': {'category':'signal_queue', 'mapped_object': (PRICE_ACTION_INTRA_DAY, INDICATOR_DOUBLE_TOP), 'mapped_fn':'get_pattern_target', 'kwargs':{'ref_point':-2, 'factor':-1}},
    'PREV_SPH': {'category':'global', 'mapped_object': 'insight_book', 'mapped_fn':'get_dist_prev_sph'},
    'PREV_SPL': {'category':'global', 'mapped_object': 'insight_book', 'mapped_fn':'get_dist_prev_spl'},
    'LAST_N_CANDLE_BODY_TARGET': {'category':'global', 'mapped_object': 'insight_book', 'mapped_fn':'get_dist_last_n_candle_high', 'kwargs':{'period':5, 'n':3}},
    'LAST_N_CANDLE_LOW': {'category':'global', 'mapped_object': 'insight_book', 'mapped_fn':'get_dist_last_n_candle_low', 'kwargs':{'period':5, 'n':3}},
    'PCT_SPOT': {'category':'local', 'mapped_object': 'insight_book', 'mapped_fn':'get_target_spot'},
    'PCT_OPTION': {'category':'local', 'mapped_object': 'insight_book', 'mapped_fn':'get_target_option'},
}


def get_signal_key(human_lang):
    if isinstance(human_lang, tuple):
        return human_lang
    else:
        return human_machine_signal_map.get(human_lang.upper(), None)


def get_target_fn(human_lang):
    return human_machine_target_map.get(human_lang.upper(), None)
