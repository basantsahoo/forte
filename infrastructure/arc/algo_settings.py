"""
algorithm_setup = {
    'NIFTY': {'strategies': ['PatternAggregator']},
    'BANKNIFTY':{'strategies': ['PatternAggregator']},
}
"""
"""
algorithm_setup = {
    'NIFTY': {'strategies': ['FridayCandleBuyFullDay', 'FridayCandleSellFullDay']},
}
"""
algorithm_setup = {
    'NIFTY': {
        'strategies': ["FridayOptionBuy", "FridayBelowVA", "FridayCandleFirst30Buy", "FridayCandleFirst30Sell"],
        'strategy_kwargs': [
            {},
            {
              "exit_time": 30
            },
            {},
            {}
        ]
    }
    #'NIFTY': {'strategies': ['ThursdayOptionSell']}
    #'NIFTY': {'strategies': ['FridayCandleBuyFullDay', 'FridayCandleSellFullDay']},
}