from market.port import Broker
br = Broker()
#br.place_intraday_market_order('NSE:SBIN-EQ',1,1)
br.place_intraday_limit_order('NSE:SBIN-EQ',1, 444.3,-1)