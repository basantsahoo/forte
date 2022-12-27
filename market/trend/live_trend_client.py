import time
import os
from settings import market_profile_db
import socketio
import rx
import rx.operators as ops
from portfolio.portfolio_manager import PortfolioManager
from config import back_test_day
default_symbols =  ['NSE:NIFTY50-INDEX', 'NSE:NIFTYBANK-INDEX']


sio = socketio.Client(reconnection_delay=5)
pm = PortfolioManager(False, '2022-04-26')
print()

@sio.event(namespace='/livefeed')
def price(input):
    global pm
    #print('received price' , input)
    #pm.price_input(list(input.values())[0])

@sio.event(namespace='/livefeed')
def connect():
    print("I'm connected!")
@sio.event(namespace='/livefeed')
def hist(input):
    #print(input)
    global pm
    import json
    x = input
    y = json.loads(x)
    # print(y['hist'])
    sym = 'NSE:NIFTYBANK-INDEX' if y['open'] > 30000 else 'NSE:NIFTY50-INDEX'
    import pandas as pd
    df = pd.DataFrame.from_dict(y['hist'], orient='index')
    df['symbol'] = sym
    df = df[['open', 'high', 'low', 'close', 'symbol']]
    df = df.reset_index()
    df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'symbol']
    recs = df.to_dict('records')
    #print(recs)
    price_list  = recs
    for price in price_list:
        pm.price_input(price)
    #pm.price_input(list(input.values())[0])


"""
@sio.event
async def connect():
    print('connected')
    await sio.emit('join_feed', default_symbols[0])
    # await sio.emit('other_message', {'socket_id': sid, 'Coneect': True}, room=sid)
"""
def connect_to_server():

    try:
        sio.connect('http://api.niftybull.in:8080', namespaces=['/livefeed'], wait_timeout=10)
        sio.emit('join_feed', default_symbols[0], namespace='/livefeed')
        sio.emit('join_feed', default_symbols[1], namespace='/livefeed')
        print('connect_to_server')
    except Exception as e:
        print(e)
        time.sleep(2)
        connect_to_server()

connect_to_server()
