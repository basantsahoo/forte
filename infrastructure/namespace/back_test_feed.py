import socketio
import json
from infrastructure.market_profile_enabler import MarketProfileEnablerService
from profile.utils import NpEncoder, get_tick_size
from db.market_data import get_daily_tick_data


class BacktestFeedNamespace(socketio.AsyncNamespace):
    def __init__(self, namespace=None):
        socketio.AsyncNamespace.__init__(self, namespace)

    def get_data(self, sym, trade_day):
        tick_df = get_daily_tick_data(sym, trade_day)
        tick_df['symbol'] = sym
        converted = tick_df.to_dict("records")
        return (x for x in converted)

    def get_price(self):
        #print('getting price')
        yield [next(pl) for pl in self.price_lst ]

    async def on_connect(self, sid, environ):
        print('connect to backtest', sid)
        await self.emit('other_message', 'connection backtest successful')

    def on_disconnect(self, sid):
        try:
            self.obs.dispose()
        except:
            pass
        print('disconnect ', sid)

    async def on_join_feed(self, sid, ticker):
        print("JOIN BY USER", ticker)
        self.enter_room(sid, ticker)


    async def on_request_data(self, sid,ticker,  back_test_date):
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
        self.pm.set_pivots(pivots)
        self.price_lst = []
        self.price_lst.append(self.get_data(ticker, back_test_date))
        obs = rx.interval(1).pipe(ops.map(lambda i: next(self.get_price())))
        loop = asyncio.get_event_loop()
        self.obs = obs.subscribe(on_next=lambda s:  rx.from_future(loop.create_task(self.on_input_feed(s))), on_error=lambda x: print('error in generator'), scheduler=AsyncIOScheduler(loop))

    async def on_exit_feed(self, sid, ticker):
        print('leave room', ticker)
        print('leave room', sid)
        self.leave_room(sid, ticker)
        #print(self.obs)
        #print(self.obs.__dict__)
        #print(dir(self.obs))

        self.obs.dispose()
        await self.emit('my_response', {'data': 'Left room: ' + ticker}, room=sid)

    async def on_input_feed(self, lst):
        print('input received')
        print(lst)
        for item in lst:
            self.processor.process_input_data(item)
            self.pm.price_input(item)
            """
            self.processor.process_input_data(item)
            price_bins = self.processor.calculateMeasures(item['symbol'])
            print(price_bins)
            if price_bins is not None:
                await self.emit('price_bins', json.dumps(price_bins, cls=NpEncoder), room=item['symbol'])
            """
            #print('emmit')
            await self.emit('price', {item['timestamp']:item}, room= item['symbol'])

