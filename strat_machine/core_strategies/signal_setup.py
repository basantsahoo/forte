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
    'TECH_PRICE_ABOVE_EMA_5': ('TECHNICAL', 'PRICE_ABOVE_EMA_5'),
    'TICK_PRICE_SIGNAL': ('PRICE', 'TICK_PRICE'),
    'CANDLE_SIGNAL': ('PRICE', 'CANDLE'),
    'STRAT_EMA_BREAK_DOWN_5': ('STRAT', 'EMA_BREAK_DOWN_5_ENTRY'),
    'WEEKLY_LEVEL_VA_H_POC_MID': ('WEEKLY_LEVEL_REACH', 'va_h_poc_mid'),
    'BULLISH_MOMENTUM': ('OPTION_MARKET', 'BULLISH_MOMENTUM'),
    'BEARISH_MOMENTUM': ('OPTION_MARKET', 'BEARISH_MOMENTUM'),
    'PCR_MINUS_1': ('OPTION_MARKET', 'PCR_MINUS_1'),
    'WEDNESDAY_15_20': ('TIME_SIGNAL', 'WEDNESDAY_15_20'),
    'WEDNESDAY_15_15': ('TIME_SIGNAL', 'WEDNESDAY_15_15'),
    'THURSDAY_09_20': ('TIME_SIGNAL', 'THURSDAY_09_20'),
    'THURSDAY_14_25': ('TIME_SIGNAL', 'THURSDAY_14_25'),
    'THURSDAY_09_45': ('TIME_SIGNAL', 'THURSDAY_09_45'),
    'FRIDAY_15_20': ('TIME_SIGNAL', 'FRIDAY_15_20'),
    'MONDAY_09_45': ('TIME_SIGNAL', 'MONDAY_09_45'),
}

human_machine_target_map = {
    'DT_HEIGHT_TARGET': {'category':'signal_queue', 'mapped_object': (PRICE_ACTION_INTRA_DAY, INDICATOR_DOUBLE_TOP), 'mapped_fn':'get_pattern_target', 'kwargs':{'ref_point':-2, 'factor':-1}},
    'SPIKE_CANDLE_HIGH': {'category':'signal_queue', 'mapped_object': ('TECHNICAL', 'CDL_5_ABOVE_EMA_5'), 'mapped_fn':'get_signal_high', 'kwargs':{}},
    'PREV_SPH': {'category':'global', 'mapped_object': 'insight_book', 'mapped_fn':'get_prev_sph'},
    'PREV_SPL': {'category':'global', 'mapped_object': 'insight_book', 'mapped_fn':'get_prev_spl'},
    'LAST_N_CANDLE_BODY_TARGET_UP': {'category':'global', 'mapped_object': 'insight_book', 'mapped_fn':'get_n_candle_body_target_up', 'kwargs':{'period':5, 'n':3}},
    'LAST_N_CANDLE_BODY_TARGET_DOwN': {'category':'global', 'mapped_object': 'insight_book', 'mapped_fn':'get_n_candle_body_target_down', 'kwargs':{'period':5, 'n':3}},
    'LAST_N_CANDLE_HIGH': {'category': 'global', 'mapped_object': 'insight_book', 'mapped_fn': 'get_last_n_candle_high', 'kwargs': {'period': 5, 'n': 3}},
    'LAST_N_CANDLE_LOW': {'category':'global', 'mapped_object': 'insight_book', 'mapped_fn':'get_last_n_candle_low', 'kwargs':{'period':5, 'n':3}},

}

default_strategy_params = {
    "id": None,
    "min_tpo": 1,
    "max_tpo": 13,
    "record_metric": True,
    "triggers_per_signal": 1,
    "max_signal": 1,
    "weekdays_allowed": [],
    "entry_signal_queues": [],  # Used for signals to be evaluated to enter a trade
    "exit_criteria_list": [],  # Used for signals to be evaluated to exit a trade
    "signal_filters": [],  # Signals that should be filtered out before sending to queue
    "register_signal_category": None,
    "entry_switch": {},
    "risk_limits": [],
    "trade_cut_off_time": 60,
}


def get_signal_key_to_be_deleted(human_lang):
    if isinstance(human_lang, tuple):
        return human_lang
    else:
        return human_machine_signal_map.get(human_lang.upper(), None)


def get_target_fn(human_lang):
    return human_machine_target_map.get(human_lang.upper(), None)

def get_startegy_args(**kwargs):
    args = {}
    arg_list = list(default_strategy_params.keys())
    #arg_list = ["id", "symbol", "order_type", "spot_instruments", "derivative_instruments", "exit_time", "exit_at", "min_tpo", "max_tpo", "record_metric", "triggers_per_signal", "max_signal","weekdays_allowed", "entry_signal_queues", "exit_criteria_list", "signal_filters", "spot_long_targets", "spot_long_stop_losses", "spot_short_targets", "spot_short_stop_losses", "instr_targets", "instr_stop_losses", "instr_to_trade", "cover", "register_signal_category", "trade_controllers", "entry_switch", "risk_limits", "carry_forward_days", "force_exit_ts", "trade_cut_off_time"]
    for arg_ in arg_list:
        #if eval(arg_):
        #args[arg_] = eval(arg_)
        args[arg_] = kwargs.get(arg_, default_strategy_params[arg_])
    return args


default_trade_manager_params = {
    "strategy_id": None,
    "asset": None,
    "durations": [10],
    "exit_at":None,
    "carry_forward_days": [0],
    "triggers_per_signal": 1,
    "force_exit_ts": None,
    "spot_high_targets": [],  # [0.002,0.003, 0.004, 0.005],
    "spot_high_stop_losses": [],  # [-0.001, -0.002, -0.002, -0.002],
    "spot_low_targets": [],  # [-0.002, -0.003, -0.004, -0.005],
    "spot_low_stop_losses": [],  # [0.001, 0.002, 0.002, 0.002],
    "spot_high_target_levels": [],
    "spot_high_stop_loss_levels": [],
    "spot_low_target_levels": [],
    "spot_low_stop_loss_levels": [],
    "trade_targets": [],  # [0.002,0.003, 0.004, 0.005],
    "trade_stop_losses": [],  # [-0.001,-0.002, -0.002,-0.002]
    "leg_group_exits": {},
    "trade_controllers": [],
    "risk_limits": [],
    "trade_info": {}
}

def get_trade_manager_args(**kwargs):
    args = {}
    arg_list = list(default_trade_manager_params.keys())
    #arg_list = ["id", "symbol", "order_type", "spot_instruments", "derivative_instruments", "exit_time", "exit_at", "min_tpo", "max_tpo", "record_metric", "triggers_per_signal", "max_signal","weekdays_allowed", "entry_signal_queues", "exit_criteria_list", "signal_filters", "spot_long_targets", "spot_long_stop_losses", "spot_short_targets", "spot_short_stop_losses", "instr_targets", "instr_stop_losses", "instr_to_trade", "cover", "register_signal_category", "trade_controllers", "entry_switch", "risk_limits", "carry_forward_days", "force_exit_ts", "trade_cut_off_time"]
    for arg_ in arg_list:
        #if eval(arg_):
        #args[arg_] = eval(arg_)
        args[arg_] = kwargs.get(arg_, default_trade_manager_params[arg_])
    return args
