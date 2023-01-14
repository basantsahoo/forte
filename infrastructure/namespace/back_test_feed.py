import socketio
import asyncio
import json
import rx
import rx.operators as ops
from rx.scheduler.eventloop import AsyncIOScheduler

from infrastructure.market_profile_enabler import MarketProfileEnablerService
from infrastructure.namespace.auth_mixin import AuthMixin
from dynamics.profile.utils import NpEncoder, get_tick_size
from db.market_data import get_daily_tick_data, get_daily_option_data_2
import helper.utils as helper_utils
from config import socket_auth_enabled
from config import back_test_day as default_back_test_day


class BacktestFeedNamespace(socketio.AsyncNamespace, AuthMixin):
    def __init__(self, namespace=None):
        socketio.AsyncNamespace.__init__(self, namespace)

    def get_data(self, sym, trade_day):
        tick_df = get_daily_tick_data(sym, trade_day)
        tick_df['symbol'] = sym
        tick_df['ltp'] = tick_df['close']
        converted = tick_df.to_dict("records")
        return (x for x in converted)

    def get_option_data(self, sym, trade_day):
        option_df = get_daily_option_data_2(sym, trade_day)
        ts_list = list(option_df['timestamp'].unique())
        converted = []
        for ts in ts_list:
            t_df = option_df[option_df['timestamp'] == ts][['instrument', 'oi', 'volume', 'open', 'high', 'low', 'close']]
            t_df['ltt'] = ts
            t_df['ltp'] = t_df['close']
            #t_df.set_index('instrument', inplace=True)
            recs = t_df.to_dict('records')
            for rec in recs:
                [strike, kind] = rec['instrument'].split("_")
                rec['strike'] = strike
                rec['type'] = kind
            converted.append({'timestamp': ts, 'symbol': sym, 'data': recs})
        return (x for x in converted)

    def get_price(self):
        #print('getting price')
        yield [next(pl) for pl in self.price_lst ]

    def get_option_price(self):
        #print('getting price')
        yield [next(pl) for pl in self.option_lst]


    async def on_connect(self, sid,environ, auth={}):
        print('AUTH++++++++++++', auth)
        if not socket_auth_enabled or (socket_auth_enabled and self.is_authenticated(auth)):
            await self.emit('other_message', 'connection successful')
        else:
            raise socketio.exceptions.ConnectionRefusedError('authentication failed')

    def on_disconnect(self, sid):
        try:
            self.obs.dispose()
        except:
            pass
        print('disconnect ', sid)

    async def on_get_trade_date(self, sid):
        print("TRADE DATE BY USER")
        await self.emit('set_trade_date', default_back_test_day, room=sid)

    async def on_join_tick_feed(self, sid, ticker):
        print("JOIN BY USER", ticker)
        self.enter_room(sid, ticker)
        #await self.on_request_data(sid,ticker)


    async def on_request_data(self, sid,ticker, back_test_date=None):
        if back_test_date is None:
            back_test_date = default_back_test_day
        print("DATA REQUEST BY USER", back_test_date)
        self.processor = MarketProfileEnablerService()
        self.processor.socket = self
        self.processor.set_trade_day(back_test_date)
        ltp = self.processor.get_ltp(ticker)
        tick_size = get_tick_size(ltp)
        await self.emit('tick_size', tick_size, room=sid)
        await self.emit('ltp', ltp, room=sid)
        pivots = self.processor.get_pivots(ticker)
        yday_data = self.processor.get_prev_day_profile(ticker)
        #print(yday_data)
        pivots['y_va_h_p'] = yday_data['va_h_p']
        pivots['y_va_l_p'] = yday_data['va_l_p']
        pivots['y_poc'] = yday_data['poc_price']
        await self.emit('pivots', pivots, room=sid)
        #self.pm.set_pivots(pivots)
        self.price_lst = []
        self.price_lst.append(self.get_data(ticker, back_test_date))
        self.option_lst = []
        self.option_lst.append(self.get_option_data(ticker, back_test_date))

        obs = rx.interval(0.2).pipe(ops.map(lambda i: next(self.get_price())))
        obs2 = rx.interval(0.2).pipe(ops.map(lambda i: next(self.get_option_price())))
        loop = asyncio.get_event_loop()
        self.obs = obs.subscribe(on_next=lambda s:  rx.from_future(loop.create_task(self.on_input_feed(s))), on_error=lambda x: print('error in generator'), scheduler=AsyncIOScheduler(loop))
        self.obs2 = obs2.subscribe(on_next=lambda s: rx.from_future(loop.create_task(self.on_option_input_feed(s))), on_error=lambda x: print('error in generator'), scheduler=AsyncIOScheduler(loop))

    async def on_exit_feed(self, sid, ticker):
        print('leave room', ticker)
        print('leave room', sid)
        self.leave_room(sid, ticker)
        #print(self.obs)
        #print(self.obs.__dict__)
        #print(dir(self.obs))

        self.obs.dispose()
        await self.emit('my_response', {'data': 'Left room: ' + ticker}, room=sid)

    async def on_join_options_feed(self, sid, ticker):
        self.enter_room(sid, helper_utils.get_options_feed_room(ticker))

    async def on_option_input_feed(self, lst):
        #print('input option received', lst)
        for item in lst:
            await self.emit('all_option_data', json.dumps(item, cls=NpEncoder), room= helper_utils.get_options_feed_room(item['symbol']))
            #await self.emit('all_option_data', item, room=helper_utils.get_options_feed_room(item['symbol']))


    async def on_input_feed(self, lst):
        print('input received')
        print(lst)
        for item in lst:
            """
            self.processor.process_input_data(item)
            self.pm.price_input(item)
            """
            """
            self.processor.process_input_data(item)
            price_bins = self.processor.calculateMeasures(item['symbol'])
            print(price_bins)
            if price_bins is not None:
                await self.emit('price_bins', json.dumps(price_bins, cls=NpEncoder), room=item['symbol'])
            """
            #print('emmit')
            await self.emit('tick_data', {item['timestamp']:item}, room= item['symbol'])

