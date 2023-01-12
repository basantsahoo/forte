import socketio
import pandas as pd
import json
import numpy as np
import math
from datetime import datetime, date
from collections import OrderedDict
import time
import pytz
import sys
from infrastructure.market_profile_enabler import MarketProfileEnablerService, TickMarketProfileEnablerService
from infrastructure.arc.oms_portfolio import OMSPortfolioManager
from infrastructure.namespace.auth_mixin import AuthMixin
from dynamics.profile.options_profile import OptionProfileService
from dynamics.profile.utils import NpEncoder, get_tick_size
from db.market_data import get_daily_tick_data
from config import live_feed, place_live_orders, socket_auth_enabled, allowed_apps
import helper.utils as helper_utils
from py_vollib_vectorized import price_dataframe
from config import get_expiry_date, rest_api_url
import requests
from servers.server_settings import cache_dir
from diskcache import Cache
option_rooms = [helper_utils.get_options_feed_room('NIFTY'), helper_utils.get_options_feed_room('BANKNIFTY')]


class LiveFeedNamespace(socketio.AsyncNamespace, AuthMixin):
    def __init__(self,namespace=None):
        socketio.AsyncNamespace.__init__(self,namespace)
        self.market_cache = Cache(cache_dir + 'market_cache')
        self.processor = TickMarketProfileEnablerService(market_cache=self.market_cache)
        self.option_processor = OptionProfileService(market_cache=self.market_cache)
        self.processor.socket = self
        self.option_processor.socket = self
        #self.portfolio_manager = OMSPortfolioManager(place_live_orders=True, market_cache=self.market_cache)
        #print(self.market_cache.get('trends'))
        self.hist_insight = self.market_cache.get('hist_insight', [])
        self.latest_option_data = self.market_cache.get('latest_option_data', {})
        self.trends = {}

    def refresh(self):
        self.market_cache.set('hist_insight', [])
        self.market_cache.set('price_data', {})
        self.market_cache.set('option_data', {})
        self.market_cache.set('latest_option_data', {})

    async def on_connect(self, sid,environ, auth={}):
        print('AUTH++++++++++++', auth)
        if not socket_auth_enabled or (socket_auth_enabled and self.is_authenticated(auth)):
            await self.emit('other_message', 'connection successful')
        else:
            raise socketio.exceptions.ConnectionRefusedError('authentication failed')


    def on_disconnect(self, sid):
        print('disconnect ', sid)

    async def on_get_trade_date(self, sid):
        print("TRADE DATE BY USER")
        datetime.date.today()

        await self.emit('set_trade_date', date.today(), room=sid)

    """
    Market Insight starts
    """
    async def on_join_market_insight(self, sid):
        print("JOIN market_analytics BY USER", sid)
        self.enter_room(sid, 'market_insight')

        for ticker in ['NIFTY', 'BANKNIFTY']:
            pivots = self.processor.get_pivots(ticker)
            yday_data = self.processor.get_prev_day_profile(ticker)
            #print(yday_data)
            pivots['y_va_h_p'] = yday_data['va_h_p']
            pivots['y_va_l_p'] = yday_data['va_l_p']
            pivots['y_poc'] = yday_data['poc_price']
            pivots['symbol'] = ticker
            await self.emit('insight', {'type': 'pivots', 'insight': pivots}, room=sid)

        for insight in self.hist_insight:
            await self.emit('insight', {'type': 'pattern', 'insight': insight}, room=sid)
        saved_trends = self.market_cache.get('trends', {})
        for sym, sym_trend in saved_trends.items():
            trend_data = {"pattern": "TREND", "symbol": sym, "info" : {"trend": sym_trend}}
            await self.emit('insight', {'type': 'pattern', 'insight': json.dumps(trend_data)}, room=sid)
        """
        for ticker in ['NIFTY', 'BANKNIFTY']:
            spot_data = self.market_cache.get(helper_utils.root_symbol(ticker))
            if spot_data is not None:
                spot_data['symbol'] = helper_utils.root_symbol(ticker)
                await self.send_market_insight('price', spot_data)
        """

    async def on_exit_market_insight(self, sid):
        self.leave_room(sid, 'market_insight')

    async def send_market_insight(self, category, info):
        if category == 'pattern':
            j_info = json.loads(info)
            if j_info['pattern'] == 'STATE':
                if j_info['info']['signal'] == 'open_type':
                    self.hist_insight.append(info)
            elif j_info['pattern'] != 'TREND':
                self.hist_insight.append(info)
            else:
                self.trends[j_info['symbol']] = j_info['info']['trend']
                self.market_cache.set('trends', self.trends) #1 THIS GETS OVERWRITTEN
            self.market_cache.set('hist_insight', self.hist_insight) #2 THIS NEEDS REFRESH EVERYDAY

        await self.emit('insight', {'type': category, 'insight': info}, room='market_insight')

    """
    Market Insight ends
    """

    """
    Tick data and pivots start
    """

    async def on_get_price_chart_data(self, sid, ticker):
        await self.send_pivot_values(sid, ticker)
        print("JOIN PRICE CHART FEED BY USER", ticker)
        spot_data = self.market_cache.get(helper_utils.root_symbol(ticker))
        ltp = spot_data['close'] #-----------------------------------------
        tick_size = get_tick_size(ltp)
        await self.emit('tick_size', {'symbol':ticker, 'data':tick_size}, room=sid)
        hist_data = self.processor.get_hist_data(ticker)
        #print(hist_data)
        if hist_data is not None:
            hist_data['symbol'] = ticker
            await self.emit('hist', json.dumps(hist_data, cls=NpEncoder), room=sid)
        else:
            await self.emit('tick_data', {spot_data['timestamp']: spot_data}, room=sid)

    async def on_get_last_feed(self, sid, ticker):
        await self.send_pivot_values(sid, ticker)
        print("on_get_last_feed++++++++++", ticker)
        spot_data = self.market_cache.get(helper_utils.root_symbol(ticker))
        await self.emit('tick_data', {spot_data['timestamp']: spot_data}, room=sid)

    async def send_pivot_values(self, sid, ticker):
        print('sending pivot values')
        pivots = self.processor.get_pivots(ticker)
        yday_data = self.processor.get_prev_day_profile(ticker)
        pivots['y_va_h_p'] = yday_data['va_h_p']
        pivots['y_va_l_p'] = yday_data['va_l_p']
        pivots['y_poc'] = yday_data['poc_price']
        pivots['symbol'] = ticker
        await self.emit('pivots', pivots, room=sid)

    async def on_join_tick_feed(self, sid, ticker):
        self.enter_room(sid, ticker)

    async def on_exit_feed(self, sid, ticker):
        print('leave room', ticker)
        self.leave_room(sid, ticker)
        await self.emit('my_response', {'data': 'Left room: ' + ticker}, room=sid)

    async def on_input_feed(self, sid, lst):
        print('on_input_feed++++')
        for item in lst:
            item = helper_utils.standardize_feed(item)
            ## following 2 lines are for testing only
            #print(item)
            #item['ltp'] = item['close']
            #item['min_volume'] = 0
            #item['symbol'] = helper_utils.root_symbol(item['symbol'])
            item = self.processor.process_input_data(item)
            price_bins = self.processor.calculateMeasures(item['symbol'])
            if price_bins is not None:
                await self.emit('price_bins', json.dumps(price_bins, cls=NpEncoder), room=item['symbol'])
            await self.emit('tick_data', {item['timestamp']:item}, room= item['symbol'])


    async def on_td_price_feed(self, sid, feed):
        print('td feed received')
        feed['symbol'] = helper_utils.root_symbol(feed['symbol'])
        epoch_tick_time = int(datetime.fromisoformat(feed['timestamp'] + '+05:30').timestamp())
        feed['timestamp'] = epoch_tick_time
        feed['min_volume'] = feed['volume'] if 'volume' in feed else 0
        self.option_processor.process_spot_data(feed)
        item = self.processor.process_input_data(feed)
        print(item)
        await self.emit('tick_data', {item['timestamp']: item}, room=item['symbol'])
        ley_list = ['symbol', 'ltp', "day_high", "day_low", "volume"]
        feed_small = {key: feed[key] for key in ley_list if key in feed}
        print(feed_small)
        for room in option_rooms:
            await self.emit('spot_data', feed_small, room=room)
        self.market_cache.set(item['symbol'], item) #3 Gets overwritten

    """
    Tick data and pivot ends
    """

    async def on_get_hist_option_data(self, sid, ticker):
        print("JOIN OPTION FEED BY USER", helper_utils.root_symbol(ticker))
        start_time = datetime.now()
        hist_data = self.option_processor.get_hist_data(helper_utils.get_oc_symbol(ticker))
        t_df = pd.DataFrame(hist_data)
        #t_df.to_csv('hist_option.csv')
        end_time = datetime.now()
        print('on_get_hist_option_data', (end_time - start_time).total_seconds())

        if hist_data is not None:

            imp_strikes = self.option_processor.important_strikes[ticker]
            await self.emit('imp_strikes', {'symbol': ticker, 'data': imp_strikes}, room=sid)
            await self.emit('hist_option_data', {'symbol': ticker, 'data': hist_data}, room=sid)

    async def on_get_last_option_tick(self, sid, ticker):
        option_data = self.market_cache.get('latest_option_data',{}).get(helper_utils.root_symbol(ticker))
        if option_data:
            #option_data = [inst_data  for inst_data in option_data if self.option_processor.filtered_option(ticker, inst_data)]
            await self.emit('all_option_data', {'symbol':ticker, 'data':option_data}, room=sid)

    async def on_join_options_feed(self, sid, ticker):
        self.enter_room(sid, helper_utils.get_options_feed_room(ticker))


    async def on_exit_option_feed(self, sid, ticker):
        print('leave option feed room', sid, ticker)
        self.leave_room(sid, helper_utils.get_options_feed_room(ticker))
        await self.emit('my_response', {'data': 'Left room: ' + ticker}, room=sid)

    async def on_td_oc_feed(self, sid, feed):
        #print('oc feed', feed)
        self.option_processor.process_input_data(feed)

    async def on_td_option_price_feed(self, sid, feed):
        #print('on_td_option_price_feed' , feed)
        await self.emit('atm_option_feed', feed, room='atm_option_room')
        #self.portfolio_manager.option_price_input(feed)

    async def all_option_input(self, symbol, recent_changes):
        self.latest_option_data[symbol] = recent_changes
        await self.emit('all_option_data', {'symbol':symbol, 'data':recent_changes}, room=helper_utils.get_options_feed_room(symbol))
        self.market_cache.set('latest_option_data', self.latest_option_data) #4. Gets overwritten

    async def important_strikes_update(self, symbol, recent_changes):
        await self.emit('imp_strikes', {'symbol':symbol, 'data':recent_changes}, room=helper_utils.get_options_feed_room(symbol))

    async def on_send_pattern_signal(self, sid, pattern_info):
        print('on_send_pattern_signal in socket')
        await self.send_market_insight('pattern', pattern_info)



    async def on_scenario_analysis(self, sid, portfolio):
        df = pd.DataFrame()

        scen_flags = []
        scen_spots = []
        scen_strikes = []
        scen_ivs = []
        scen_qtys = []
        scen_multiples = []
        scen_curr_prices = []
        for position in portfolio:
            print(position)
            #spot = self.option_processor.get_spot_data(helper_utils.root_symbol(position['symbol']))
            #spot = 16700
            spot_data = self.market_cache.get(helper_utils.root_symbol(position['symbol']))
            spot = spot_data['close']  # -----------------------------------------

            #spot = self.option_processor.get_spot_data(helper_utils.root_symbol(position['symbol']))['ltp']
            spot = round(spot/100) * 100
            up_side_analyse = math.ceil(spot * 1.05/100) * 100
            down_side_analyse = math.floor(spot * 0.95 / 100) * 100
            scenarios = list(range(down_side_analyse, up_side_analyse+100, 100))
            strikes = [position['strike'] for x in scenarios]
            l_option_data = self.latest_option_data[helper_utils.root_symbol(position['symbol'])]
            iv = [option['IV'] for option in l_option_data if option['strike'] == position['strike'] and option['type'] == position['type']][0]
            #iv = 12.88/100
            ivs = [iv for x in scenarios]

            flag = 'p' if position['type'] == 'PE' else 'c'
            flags = [flag for x in scenarios]
            qty = position['qty']
            multiple = position['multiple']
            qtys = [qty for x in scenarios]
            multiples = [multiple for x in scenarios]
            scen_spots = scen_spots + scenarios
            scen_strikes = scen_strikes + strikes
            scen_ivs = scen_ivs + ivs
            scen_flags = scen_flags + flags
            scen_qtys = scen_qtys + qtys
            scen_multiples = scen_multiples + multiples
            curr_price = [option['ltp'] for option in l_option_data if option['strike'] == position['strike'] and option['type'] == position['type']][0]
            #curr_price = 138 if position['strike'] == 16700 else 440
            curr_price_lst = [curr_price for x in scenarios]
            scen_curr_prices = scen_curr_prices + curr_price_lst

        expiry_dt = get_expiry_date()
        print('+++++', expiry_dt)
        #print(helper_utils.get_time_to_expiry_from_day_end(expiry_dt) /(365 * 24 * 3600))

        df['Flag'] = scen_flags
        df['S'] = scen_spots
        df['K'] = scen_strikes
        holding_time = portfolio[0].get('holding_time', 0)
        df['T'] = helper_utils.get_time_to_expiry_from_day_end(expiry_dt) /(365 * 24 * 3600) if not holding_time else max((helper_utils.get_time_to_expiry(expiry_dt) - holding_time * 3600),0)/(365 * 24 * 3600)
        df['R'] = 10 / 100
        df['IV'] = scen_ivs
        df['qty'] = scen_qtys
        df['multiple'] = scen_multiples
        df['curr_price'] = scen_curr_prices
        expiry_df = df.copy()
        expiry_df['T'] = 0
        result = price_dataframe(df, flag_col='Flag', underlying_price_col='S', strike_col='K', annualized_tte_col='T',
                                 riskfree_rate_col='R', sigma_col='IV', model='black_scholes', inplace=True)
        #print(result)
        #print(df)
        result_exp = price_dataframe(expiry_df, flag_col='Flag', underlying_price_col='S', strike_col='K', annualized_tte_col='T',
                                 riskfree_rate_col='R', sigma_col='IV', model='black_scholes', inplace=True)
        #print(expiry_df)
        expiry_df['unit_pnl_expiry'] = (expiry_df['Price'] - expiry_df['curr_price']) * expiry_df['qty']
        expiry_df_tmp = expiry_df[['S', 'K', 'Flag', 'unit_pnl_expiry']]
        port_df = df[['S', 'K', 'qty',  'curr_price', 'Price', 'Flag', 'multiple']].copy()
        port_df['initial_inflow'] = -1 * port_df['curr_price'] * port_df['qty']
        port_df['unit_pnl'] = port_df['Price'] * port_df['qty']
        port_df['total_pnl'] = (port_df['Price'] - port_df['curr_price']) * port_df['qty'] * port_df['multiple']
        new_df = pd.merge(port_df, expiry_df_tmp, how='left', on=['S', 'K', 'Flag'])
        #print(new_df)

        def calc(rows):
            row_dict = rows.to_dict('records')
            tmp = OrderedDict()
            tmp['spot'] = row_dict[0]['S']
            for row in row_dict:
                tmp["I_" + str(row['K']) + row['Flag'].upper() + "E"] = round(row['initial_inflow'], 2)
            tmp['initial_inflow'] = 0
            for row in row_dict:
                tmp[str(row['K']) + row['Flag'].upper() + "E"] = round(row['unit_pnl'], 2)

            tmp['unit_port_pnl'] = 0

            tmp['total_port_pnl'] = 0
            tmp['unit_pnl_expiry'] = 0
            for row in row_dict:
                tmp['initial_inflow'] += row['initial_inflow']
                tmp['unit_port_pnl'] = tmp['unit_port_pnl'] + row['unit_pnl'] + row['initial_inflow']
                tmp['total_port_pnl'] += row['total_pnl']
                tmp['unit_pnl_expiry'] += row['unit_pnl_expiry']
            tmp['initial_inflow'] = round(tmp['initial_inflow'], 0)
            tmp['unit_port_pnl'] = round(tmp['unit_port_pnl'], 0)
            tmp['total_port_pnl'] = round(tmp['total_port_pnl'], 0)
            tmp['unit_pnl_expiry'] = round(tmp['unit_pnl_expiry'], 0)
            return dict(tmp)

        dd = new_df.groupby('S').apply(calc)
        await self.emit('scenario_analysis_response', list(dd), room=sid)






