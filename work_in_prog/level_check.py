import pandas as pd
from datetime import datetime
from arc.portfolio import PortfolioManager
from db.market_data import get_all_days, get_pending_key_level_days, get_prev_day_key_levels
import helper.utils as helper_utils
import traceback
from config import default_symbols
from trend.support_resistance import SupportResistance
from db.db_engine import get_db_engine
import json

"""
days = get_all_days(helper_utils.get_nse_index_symbol(symbol))
#days.reverse()
results = []
start_time = datetime.now()
existing_supports = []
existing_resistances = []
dddd = days[0:100]
dddd.reverse()
#dddd = dddd[5:10]
for day in dddd:
    print(day)
    print('=========================================================================================')
    print('resistance at begin', existing_resistances)
    print('support at begin', existing_supports)
    checker = SupportResistance(symbol,day)
    checker.existing_resistances = existing_resistances
    checker.existing_supports = existing_supports
    checker.process()
    existing_resistances = checker.existing_resistances
    existing_supports = checker.existing_supports

end_time = datetime.now()
print((end_time - start_time).total_seconds())
# print(results)
"""
def calculate(trade_days=[], symbols=[], debug=False):
    if len(symbols) == 0:
        symbols = [helper_utils.get_nse_index_symbol(symbol) for symbol in default_symbols]

    for symbol in symbols:
        tmp_trade_days = trade_days
        if len(tmp_trade_days) == 0:
            tmp_trade_days = get_pending_key_level_days(symbol)
            if len(tmp_trade_days) == 0:
                tmp_trade_days = get_all_days(helper_utils.get_nse_index_symbol(symbol))
                tmp_trade_days.reverse()
        for trade_day in tmp_trade_days:
            print(trade_day, " ", symbol)
            print('=========================================================================================')
            prev_key_levels =get_prev_day_key_levels(symbol, trade_day)
            #print(prev_key_levels)
            existing_supports = json.loads(prev_key_levels[1])
            existing_resistances = json.loads(prev_key_levels[2])
            print('resistance at begin', existing_resistances)
            print('support at begin', existing_supports)
            checker = SupportResistance(symbol, trade_day)
            checker.existing_resistances = existing_resistances
            checker.existing_supports = existing_supports
            checker.process()
            existing_resistances = checker.existing_resistances
            existing_supports = checker.existing_supports
            rec = {
                'symbol': symbol,
                'date': trade_day,
                'supports': json.dumps(checker.existing_supports),
                'resistances': json.dumps(checker.existing_resistances),
            }
            #print(rec)
            df = pd.DataFrame([rec])
            engine = get_db_engine()
            conn = engine.connect()
            df.to_sql('key_levels', conn, if_exists="append", index=False)
            if len(existing_supports) + len(existing_resistances) == 0:
                conn.execute('ALTER TABLE key_levels ADD PRIMARY KEY (symbol, date);')
            conn.close()

def run():
    calculate()


run()

