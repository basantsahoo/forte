strategy_regulator={
    'DT_SELL': {'BASANT_FYERS': {'scale':1, 'instruments': ['OPT','FUT'], 'strike' : 'ATM'}},
    'DTBRK_BUY': {'BASANT_FYERS': {'scale':1, 'instruments': ['OPT','FUT'], 'strike' : 'ATM'}},
    'CDLHIKKAKE_BUY': {'BASANT_FYERS': {'scale':2, 'instruments': ['OPT','FUT'], 'strike' : 'ATM'}},
    'CDLHIKKAKE_SELL': {'BASANT_FYERS': {'scale':2, 'instruments': ['OPT','FUT'], 'strike' : 'ATM'}},
    'CDLENGULFING_BUY': {'BASANT_FYERS': {'scale':1, 'instruments': ['OPT','FUT'], 'strike' : 'ATM'}},
    'OPTION_CHEAP': {'BASANT_FYERS': {'scale':2, 'instruments': ['OPT'], 'strike' : 'ATM'}},
    'OPTION_SELL': {'BASANT_FYERS': {'scale':1, 'instruments': ['OPT'], 'strike' : 'ATM'}},
    'BELOWVAFRI': {'BASANT_FYERS': {'scale':1, 'instruments': ['OPT'], 'strike' : 'ATM'}},
}


def get_strategy_name(strat_id):
    splt = strat_id.split("_")
    if len(splt) == 1:
        return strat_id
    else:
        return splt[0]+"_"+splt[1]


def get_strategy_regulation(strategy):
    return strategy_regulator[strategy]


def get_lot_size(index):
    return 50 if index == 'NIFTY' else 25 if index == 'BANKNIFTY' else 0



