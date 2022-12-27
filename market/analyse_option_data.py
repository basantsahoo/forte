from truedata.custom import TDCustom
td_scoket = TDCustom.getInstance()
greeks = td_scoket.get_intraday_geeks('NIFTY', option_type="PE")

greeks['IV_dif'] = greeks['IV'].diff()
greeks['spot_dif'] = greeks['Spot'].diff()
greeks['delta_dif'] = greeks['delta'].diff()
print(greeks['IV_dif'].corr(greeks['delta_dif']))
print(greeks['IV_dif'].corr(greeks['delta_dif'].shift(2)))
#greeks.to_csv('NIFTY_PE.csv')
#print(greeks)
