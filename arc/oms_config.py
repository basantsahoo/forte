strategy_regulator_o={
    'HighPutVolumeBuy': {'BASANT_FYERS': {'scale':1, 'instruments': ['OPT'], 'strike' : 'ATM'}},
    'PutBuy': {'BASANT_FYERS': {'scale':2, 'instruments': ['OPT'], 'strike' : 'ITM'}},
    'CallBuy': {'BASANT_FYERS': {'scale':2, 'instruments': ['OPT'], 'strike' : 'ITM'}},
}

strategy_regulator={
    'IRON_CONDOR_ADJUST': {'BASANT_FYERS': {'scale': 0.25}},
    'MID_WEEK_CLOSE_BELOW_VA': {'BASANT_FYERS': {'scale': 1}},
    'WEDNESDAY_RANGE_BOUND': {'BASANT_FYERS': {'scale': 1}},
    'WEDNESDAY_EOD_SHORT': {'BASANT_FYERS': {'scale': 1}}
}


def get_strategy_regulation(strategy):
    return strategy_regulator[strategy]


def get_lot_size(index):
    return 25 if index == 'NIFTY' else 15 if index == 'BANKNIFTY' else 0



