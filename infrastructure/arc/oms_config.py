strategy_regulator={
    'DT_SELL': {1: {'scale':1, 'instruments': ['OPT','FUT'], 'strike' : 'ATM'}},
    'DTBRK_BUY': {1: {'scale':1, 'instruments': ['OPT','FUT'], 'strike' : 'ATM'}},
    'CDLHIKKAKE_BUY': {1: {'scale':1, 'instruments': ['OPT','FUT'], 'strike' : 'ATM'}},
    'CDLENGULFING_BUY': {1: {'scale':1, 'instruments': ['OPT','FUT'], 'strike' : 'ATM'}},
    'OPTION_CHEAP': {1: {'scale':1, 'instruments': ['OPT'], 'strike' : 'ATM'}},
    'OPTION_SELL': {1: {'scale':1, 'instruments': ['OPT'], 'strike' : 'ATM'}},
}


def get_strategy_name(strat_id):
    splt = strat_id.split("_")
    return splt[0]+"_"+splt[1]


def get_strategy_regulation(strategy):
    return strategy_regulator[strategy]


def get_lot_size(index):
    return 50 if index == 'NIFTY' else 25 if index == 'BANKNIFTY' else 0


def get_instr_type(order_type):
    return instr_type_dict[order_type]


