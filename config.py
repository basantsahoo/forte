from datetime import datetime, date, time
va_pct = 0.7 #value area percentage
min_co_ext = 2 #no of tpos for considering extremes
"""
price_range = [50, 100, 1000, 2500, 10000, 20000, 9999999999]
tick_steps = [0.05, 0.1, 0.25, 0.5, 1, 5, 10]
"""
price_range = [50, 100, 1000, 2500, 20000, 9999999999]
tick_steps = [0.05, 0.1, 0.25, 0.5,  5, 10]

exclued_days = ['2021-11-04', '2020-11-14', '2019-10-27', '2021-02-24']
trading_halt_day = [ '2021-02-24']
include_pre_market = False

regimes = ['2018-12-10', '2019-06-12', '2020-02-20', '2020-04-03', '2020-10-03', '2021-02-15', '2021-07-26', '2021-12-10']
regime_desc = ['All 1', 'bear & reversal', 'sharp bear', 'bull & correction 1', 'sharp bull', 'All 2', 'bull & correction 2']

back_test_day = '2022-07-28' #'2021-12-09'
place_live_orders = True # determines placing of order
live_feed = True #True  #determines live tickdata or historical 1 min data
socket_auth_enabled = True
default_symbols =  ['NIFTY', 'BANKNIFTY']
rest_api_url = 'http://localhost:8000/'
order_api = rest_api_url + 'order'
allowed_apps = ['CALG136148', 'FEEDTD136148', 'FEEDFY136148']

#order_api = 'https://api.niftybull.in/order'
expiry_dt = datetime(2022, 8, 25)
future_expiry_dates = ['2022-08-25',  '2022-09-01', '2022-09-08', '2022-09-15', '2022-09-22', '2022-09-29', '2022-10-06', '2022-10-13', '2022-10-20', '2022-10-27', '2022-11-03', '2022-11-10', '2022-11-17', '2022-11-24', '2022-12-01', '2022-12-08', '2022-12-15', '2022-12-22',	'2022-12-29',
                       '2023-01-05', '2023-01-12',	'2023-01-19', '2023-01-25',	'2023-02-02',  '2023-02-09']

market_open_time = time(9, 15)
market_close_time = time(15, 30)
def get_expiry_date_o():
    return expiry_dt

def get_expiry_date(trade_day=None):
    fut_exp_dates = [datetime.strptime(x, '%Y-%m-%d').toordinal() for x in future_expiry_dates]
    t_day = date.today().toordinal() if trade_day is None else datetime.strptime(trade_day, '%Y-%m-%d').toordinal()
    expiry = min([x for x in fut_exp_dates if x >= t_day])
    return datetime.fromordinal(expiry)

def is_month_end_expiry(expiry):

    epiry_dt = datetime.strptime(expiry, '%y%m%d').toordinal()
    fut_exp_dates = [datetime.strptime(x, '%Y-%m-%d').toordinal() for x in future_expiry_dates]
    next_expiry = min([x for x in fut_exp_dates if x > epiry_dt])
    #print('expiry', expiry)
    #print('next_expiry', datetime.fromordinal(next_expiry))
    #print('next_expiry', date.fromordinal(epiry_dt).month != date.fromordinal(next_expiry).month)
    return date.fromordinal(epiry_dt).month != date.fromordinal(next_expiry).month

#default_symbols =  ['NSE:NIFTY50-INDEX', 'NSE:NIFTYBANK-INDEX']
'https://www1.nseindia.com/products/content/equities/indices/sectoral_indices.htm'



nifty_constituents = ['ADANIENT',
'ADANIPORTS',
'APOLLOHOSP',
'ASIANPAINT',
'AXISBANK',
'BAJAJ-AUTO',
'BAJFINANCE',
'BAJAJFINSV',
'BPCL',
'BHARTIARTL',
'BRITANNIA',
'CIPLA',
'COALINDIA',
'DIVISLAB',
'DRREDDY',
'EICHERMOT',
'HCLTECH',
'HDFCBANK',
'HDFCLIFE',
'HEROMOTOCO',
'HINDALCO',
'HINDUNILVR',
'HDFC',
'ICICIBANK',
'ITC',
'INDUSINDBK',
'INFY',
'JSWSTEEL',
'KOTAKBANK',
'M&M',
'MARUTI',
'NTPC',
'NESTLEIND',
'ONGC',
'RELIANCE',
'SBIN',
'SUNPHARMA',
'TATACONSUM',
'TATAMOTORS',
'TATASTEEL',
'TECHM',
'TITAN',
'UPL',
'ULTRACEMCO',
'WIPRO']

bank_nifty_constituents = ['AUBANK',
'AXISBANK',
'BANDHANBNK',
'BANKBARODA',
'FEDERALBNK',
'HDFCBANK',
'ICICIBANK',
'IDFCFIRSTB',
'INDUSINDBK',
'KOTAKBANK',
'PNB',
'SBIN']

stocks = ['BANKNIFTY',
'NIFTY',
'RELIANCE',
'TATASTEEL',
'TCS',
'HDFC',
'INFY',
'SAIL',
'SBIN',
'INDUSINDBK',
'ITC',
'BAJFINANCE',
'MARUTI',
'IRCTC',
'HDFCBANK',
'BHARTIARTL',
'AXISBANK',
'TATAMOTORS',
'ESCORTS',
'DRREDDY',
'ICICIBANK']

mappeer = {
    'stock': 'INFY',
    'cash': 'EQ INFY',
    'fut': 'EQ INFY',
    'options': {},
}


"""
multiply by 1%
<50 5    
50-100 10
100-1000 25
1000 - 2500 50
2500- 10000 100
10000 - 20000 500
> 20000 - 1000 

"""

"""
rules :------------
candle is named by start minute/hour/day


Trading on the equities segment takes place on all days of the week (except Saturdays and Sundays and holidays declared by the Exchange in advance). The market timings of the equities segment are:

A) Pre-open session
Order entry & modification Open: 09:00 hrs
Order entry & modification Close: 09:08 hrs*
*with random closure in last one minute. Pre-open order matching starts immediately after close of pre-open order entry.
B) Regular trading session
Normal / Limited Physical Market Open: 09:15 hrs
Normal / Limited Physical Market Close: 15:30 hrs
C) Closing Session
The Closing Session is held between 15.40 hrs and 16.00 hrs
D) Block Deal Session Timings:
Morning Window: This window shall operate between 08:45 AM to 09:00 AM.
Afternoon Window: This window shall operate between 02:05 PM to 2:20 PM.
Note:

The Exchange may, however, close the market on days other than the above schedule holidays or may open the market on days originally declared as holidays. The Exchange may also extend, advance or reduce trading hours when its deems fit and necessary.


"""

"""
Expiry day option selling can give maximum profile % as some of them becomes zero. 
On the other day because of theta percentage return is less
"""


"""
Strategy :1 
On gap up days we can take a sell trade  15 mins after market open
Position size can be done based on the return in 15 mins and subsequently 

"""

"""
Data issues

5th Aug 2021
"""