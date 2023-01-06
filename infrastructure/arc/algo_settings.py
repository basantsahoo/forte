"""
algorithm_setup = {
    'NIFTY': {'strategies': ['PatternAggregator']},
    'BANKNIFTY':{'strategies': ['PatternAggregator']},
}
"""

algorithm_setup = {
    'NIFTY': {'strategies': ['FridayCandleBuyFullDay', 'FridayCandleSellFullDay']},
}