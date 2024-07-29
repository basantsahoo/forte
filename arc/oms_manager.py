import copy
import json
import time
import numpy as np
import pandas as pd
from helper.utils import root_symbol, get_broker_order_type, get_exit_order_type
from infrastructure.broker.broker import BrokerLive
from arc.dummy_broker import DummyBroker
from arc import oms_config


class OMSManager:
    def __init__(self, place_live_orders=False, trade_date=None, data_interface=None, market_cache=None):
        self.trade_date = trade_date
        self.ltps = {}
        self.market_cache = market_cache
        self.atm_options = {'NIFTY_CE': {'strike': 17000, 'price':55, 'spot': 16735, 'expiry': '240725'},
                            'NIFTY_PE': {'strike': 15500, 'price':32, 'spot': 15877, 'expiry': '240725'},
                            'BANKNIFTY_PE': {'strike': 32000, 'price':10, 'spot': 32500, 'expiry': '240725'}}
        self.last_times = {}
        self.order_book = {}
        self.position_book = {}
        self.initial_capital = 10000
        self.max_loss = 0.05
        self.performance = {}
        self.strategy_order_map = {}
        self.brokers = []
        self.dummy_broker = None
        self.manual_positions = {}
        self.load_from_cache()
        if place_live_orders:
            self.set_live()


    def load_from_cache(self):
        print('load_from_cache oms data+++++++++++++++++++++')
        if self.market_cache is not None:
            manual_positions = self.market_cache.get('manual_positions')
            if manual_positions is not None:
                self.manual_positions = manual_positions
                for pos_id, pos in manual_positions.items():
                    self.position_book[pos_id] = pos
                """
                del self.position_book['MNMNMNMNMN20']
                self.market_cache.set('manual_positions', self.position_book)
                """

    """required for servers market trades"""
    def set_live_broker(self):
        self.brokers.append(BrokerLive(self))
        #self.prepare_positions()

    def prepare_positions(self):
        print(self.brokers[0].get_current_positions())
        all_positions = self.brokers[0].get_current_positions().get('netPositions', [])
        #print(all_positions)
        pos_map = {}
        for position in all_positions:
            if not position['symbol'] in pos_map:
                pos_map[position['symbol']] = {'quantity':0, 'portfolio_value':0}
            pos_map[position['symbol']]['quantity'] += position['netQty']
            pos_map[position['symbol']]['portfolio_value'] += position['buyVal'] - position['sellVal']
        #print('net position map')
        #print(pos_map)
        segregated_pos_map = {}
        for sig, sig_legs in self.position_book.items():
            segregated_pos_map[sig] = sig_legs
            for leg in sig_legs:

                if leg['symbol'] in pos_map:
                    pos_map[leg['symbol']]['quantity'] -= leg['side']*leg['qty']
                    pos_map[leg['symbol']]['portfolio_value'] -= leg['side'] * leg['qty']*leg['traded_price']

        segregated_pos_map['portal'] = []
        for symbol, pos in pos_map.items():
            if pos['quantity'] != 0:
                segregated_pos_map['portal'].append({'symbol':symbol, 'qty': abs(pos['quantity']), 'traded_price': pos['portfolio_value']/pos['quantity'], 'side': np.sign(pos['quantity'])})
        #print('strategy position map')
        #print(segregated_pos_map)
        return segregated_pos_map

    """required for storing trades in trader db"""
    def set_dummy_broker(self):
        self.dummy_broker = DummyBroker()

    def set_live(self):
        self.set_live_broker()
        self.set_dummy_broker()

    def get_positions(self):
        return self.prepare_positions()

    def option_price_input(self, input):
        #print('option_price_input-----', input)
        for item in input:
            self.atm_options[item[0]] = {'strike': item[1], 'price':item[2], 'spot': item[3], 'expiry': item[4]}
            #print(self.atm_options)

    def get_allowed_brokers(self, broker_ids):
        filtered_brokers = [broker for broker in self.brokers if broker.id in broker_ids]
        return filtered_brokers

    def get_instr_type(self, side, instruments):
        if side == 1 and 'OPT' in instruments:
            return ('CE', 1)
        elif side == 1 and 'FUT' in instruments:
            return ('FUT', 1)
        elif side == -1 and 'OPT' in instruments:
            return ('PE', 1)
        elif side == -1 and 'FUT' in instruments:
            return ('FUT', -1)

    def get_manual_entry_order_info(self, order_info):
        index = root_symbol(order_info['symbol'])
        lot_size = oms_config.get_lot_size(index)
        side = get_broker_order_type(np.sign(order_info['qty']))
        inst = order_info['type']
        key = index + "_" + inst
        instrument = self.atm_options[key].copy()
        instrument['underlying'] = index
        instrument['strike'] = order_info['strike']
        instrument['type'] = inst
        instrument['side'] = side
        instrument['qty'] = abs(order_info['qty'] * lot_size)
        #print('instrument++++++', instrument)
        return instrument

    def get_optimal_entry_order_info(self, order_info, strategy_regulation):

        index = root_symbol(order_info['asset'])
        lot_size = oms_config.get_lot_size(index)
        #print('lot_size==============', lot_size)
        order_info['qty'] = order_info['quantity'] * lot_size * strategy_regulation['scale']
        #print('get_optimal_entry_order_info++++', order_info)
        return order_info

    def get_optimal_exit_order_info(self, order_info, strategy_regulation):
        print('get_optimal_exit_order_info+++++', order_info)
        index = root_symbol(order_info['symbol'])
        lot_size = oms_config.get_lot_size(index)

        t_key = order_info['order_id']
        instrument = {}
        if t_key in self.strategy_order_map:
            existing_order = self.strategy_order_map[t_key]
            print(existing_order)
            instrument['symbol'] = existing_order['symbol']
            instrument['side'] = get_exit_order_type(existing_order['side'])
            instrument['qty'] = order_info['qty'] * lot_size * strategy_regulation['scale']
        #print('instrument++++++', instrument)
        return instrument

    def price_input(self, input):
        #print('price input', input)
        self.ltps[input['symbol']] = input['close']
        self.last_times[input['symbol']] = input['timestamp']
        self.evaluate_risk()
        self.monitor_position()

    def monitor_position(self):
        pass

    def place_entry_order(self, signal_info, order_type='MARKET'):
        #print('place_entry_order inside oms', json.dumps(signal_info))
        strategy_id = signal_info['strategy_id']
        signal_id = signal_info['signal_id']
        trade_set = signal_info['trade_set']

        all_orders = [leg for trade in trade_set for leg_group in trade['leg_groups'] for leg in leg_group['legs']]
        flattened_orders = [{'full_code': order['instrument']['full_code'], 'symbol': order['instrument']['symbol'], 'order_side': order['order_type'],
                             'asset': order['instrument']['asset'], 'kind':order['instrument']['kind'], 'strike': order['instrument'].get('strike', 0),
                             'quantity': abs(order['quantity'])} for order in all_orders]
        order_df = pd.DataFrame(flattened_orders)
        grouped_order_df = order_df.groupby(['full_code', 'symbol', 'order_side', 'asset', 'strike', 'kind']).agg({'quantity': ['sum']})
        grouped_order_df = grouped_order_df.reset_index()
        grouped_order_df.columns = ['full_code', 'symbol', 'order_side', 'asset', 'strike', 'kind', 'quantity']
        grouped_order_df['order_side'] = grouped_order_df['order_side'].apply(lambda x: get_broker_order_type(x))
        sorted_grouped_order_df = grouped_order_df.sort_values(by='order_side', ascending=False)

        final_orders = sorted_grouped_order_df.to_dict('records')
        response = []
        strategy_regulation = oms_config.get_strategy_regulation(strategy_id)

        for order in final_orders:
            self.strategy_order_map[signal_id] = {}
            order['option_signal'] = order['kind'] in ['CE', 'PE']
            order['strategy_id'] = strategy_id
            order['order_type'] = order_type

            allowed_brokers = self.get_allowed_brokers(list(strategy_regulation.keys()))
            for broker in allowed_brokers:
                optimal_order = self.get_optimal_entry_order_info(order, strategy_regulation[broker.id])
                res = broker.place_entry_order(optimal_order)
                response.append(res)

        if all([res['success'] for res in response]):
            for trade in trade_set:
                for leg_group in trade['leg_groups']:
                    for leg in leg_group['legs']:
                        self.strategy_order_map[(strategy_id, signal_id, trade['trade_seq'], leg_group['lg_id'], leg['leg_id'])] = {leg['instrument']['symbol']: leg['quantity']}
                    """
                    self.dummy_broker.place_order(order_info['strategy_id'], order_info['order_id'], None, res['symbol'], res['side'], 0, res['qty'],
                                                  trade_date, order_time)
                    """
        return response

    def place_exit_order_0(self, signal_info, order_type='MARKET'):
        #print('place_exit_order inside oms', json.dumps(signal_info))
        strategy_id = signal_info['strategy_id']
        signal_id = signal_info['signal_id']
        trade_set = signal_info['trade_set']
        oms_order_info = {'strategy_id': signal_info['strategy_id'], 'signal_id': signal_info['signal_id'], 'trade_set': []}
        strategy_regulation = oms_config.get_strategy_regulation(strategy_id)
        for trade in trade_set:
            trade_seq = trade['trade_seq']
            oms_trade_info = {'trade_seq': trade_seq, 'leg_groups': []}
            for leg_group in trade['leg_groups']:
                leg_group_id = leg_group['lg_id']
                oms_leg_group_info = {'lg_id': leg_group_id, 'legs': []}
                for leg in leg_group['legs']:
                    leg_id = leg['leg_id']
                    t_key = (strategy_id, signal_id, trade_seq, leg_group_id, leg_id)
                    if t_key not in self.strategy_order_map or sum(list(self.strategy_order_map[t_key].values())) == 0:
                        oms_leg_group_info['legs'].append(copy.deepcopy(leg))
                    if t_key in self.strategy_order_map and sum(list(self.strategy_order_map[t_key].values())) != 0:
                        oms_leg_group_info['legs'].append(copy.deepcopy(leg))
                oms_trade_info['leg_groups'].append(oms_leg_group_info)
            oms_order_info['trade_set'].append(oms_trade_info)
        all_orders = [leg for trade in oms_order_info['trade_set'] for leg_group in trade['leg_groups'] for leg in leg_group['legs']]
        flattened_orders = [{'full_code': order['instrument']['full_code'], 'symbol': order['instrument']['symbol'], 'order_side': order['order_type'],
                             'asset': order['instrument']['asset'], 'kind':order['instrument']['kind'], 'strike': order['instrument'].get('strike', 0),
                             'quantity': abs(order['quantity'])} for order in all_orders]
        order_df = pd.DataFrame(flattened_orders)

        grouped_order_df = order_df.groupby(['full_code', 'symbol', 'order_side', 'asset', 'strike', 'kind']).agg({'quantity': ['sum']})
        grouped_order_df = grouped_order_df.reset_index()
        grouped_order_df.columns = ['full_code', 'symbol', 'order_side', 'asset', 'strike', 'kind', 'quantity']
        grouped_order_df['order_side'] = grouped_order_df['order_side'].apply(lambda x: get_broker_order_type(x))
        sorted_grouped_order_df = grouped_order_df.sort_values(by='order_side', ascending=False)

        final_orders = sorted_grouped_order_df.to_dict('records')
        print('final_orders=======', final_orders)
        response = []
        for order in final_orders:
            self.strategy_order_map[signal_id] = {}
            order['order_side'] = get_broker_order_type(order['order_side'])
            order['option_signal'] = order['kind'] in ['CE', 'PE']
            order['strategy_id'] = strategy_id
            order['order_type'] = order_type

            allowed_brokers = self.get_allowed_brokers(list(strategy_regulation.keys()))
            for broker in allowed_brokers:
                optimal_order = self.get_optimal_entry_order_info(order, strategy_regulation[broker.id])
                res = broker.place_exit_order(optimal_order)
                response.append(res)

        if all([res['success'] for res in response]):
            for trade in oms_order_info['trade_set']:
                for leg_group in trade['leg_groups']:
                    for leg in leg_group['legs']:
                        print(leg)
                        if leg['instrument']['symbol'] in self.strategy_order_map.get((strategy_id, signal_id, trade['trade_seq'], leg_group['lg_id'], leg['leg_id']), {}):
                            self.strategy_order_map[(strategy_id, signal_id, trade['trade_seq'], leg_group['lg_id'], leg['leg_id'])][leg['instrument']['symbol']] += leg['quantity'] * leg['order_type']
        print('final self.strategy_order_map =========', self.strategy_order_map)
        return response


    def place_exit_order(self, signal_info, order_type='MARKET'):
        #print('place_exit_order inside oms', json.dumps(signal_info))
        strategy_id = signal_info['strategy_id']
        signal_id = signal_info['signal_id']
        strategy_regulation = oms_config.get_strategy_regulation(strategy_id)
        all_orders = [leg for trade in signal_info['trade_set'] for leg_group in trade['leg_groups'] for leg in leg_group['legs']]
        flattened_orders = [{'full_code': order['instrument']['full_code'], 'symbol': order['instrument']['symbol'], 'order_side': order['order_type'],
                             'asset': order['instrument']['asset'], 'kind':order['instrument']['kind'], 'strike': order['instrument'].get('strike', 0),
                             'quantity': abs(order['quantity'])} for order in all_orders]
        order_df = pd.DataFrame(flattened_orders)

        grouped_order_df = order_df.groupby(['full_code', 'symbol', 'order_side', 'asset', 'strike', 'kind']).agg({'quantity': ['sum']})
        grouped_order_df = grouped_order_df.reset_index()
        grouped_order_df.columns = ['full_code', 'symbol', 'order_side', 'asset', 'strike', 'kind', 'quantity']
        grouped_order_df['order_side'] = grouped_order_df['order_side'].apply(lambda x: get_broker_order_type(x))
        sorted_grouped_order_df = grouped_order_df.sort_values(by='order_side', ascending=False)
        final_orders = sorted_grouped_order_df.to_dict('records')
        print('final_orders=======', final_orders)
        response = []
        for order in final_orders:
            self.strategy_order_map[signal_id] = {}
            order['order_side'] = get_broker_order_type(order['order_side'])
            order['option_signal'] = order['kind'] in ['CE', 'PE']
            order['strategy_id'] = strategy_id
            order['order_type'] = order_type

            allowed_brokers = self.get_allowed_brokers(list(strategy_regulation.keys()))
            for broker in allowed_brokers:
                optimal_order = self.get_optimal_entry_order_info(order, strategy_regulation[broker.id])
                res = broker.place_exit_order(optimal_order)
                response.append(res)
        return response

    def reached_risk_limit(self, strat_id):
        return False

    def evaluate_risk(self):
        pnl = 0
        for key, str_details in self.position_book.items():
            for trigger in str_details['position'].values():
                exit_order_type = get_exit_order_type(trigger['side'])
                trigger['un_realized_pnl'] = exit_order_type * trigger['curr_qty'] * (trigger['entry_price'] - self.ltps[key[0]])
        """
                pnl += trigger['realized_pnl']
                pnl += trigger['un_realized_pnl']
        if pnl < -1 * self.max_loss * self.initial_capital:
            for strategy in self.strategies:
                strategy.trigger_force_exit_all()
        """

    def manual_signal(self, orders, trade_time=None):
        print('manual_signal', orders)
        if self.trade_date is None: #Hack
            self.trade_date = time.strftime('%Y-%m-%d')
        self.market_cache.add('manual_order_count', 0)
        all_orders = []
        all_orders_success = True
        for order in orders:
            optimal_order = self.get_manual_entry_order_info(order)
            for broker in self.brokers:
                res = broker.place_entry_order(optimal_order, 'MARKET')
                all_orders_success = all_orders_success and res['success']
                all_orders.append(res)

        if all_orders_success and len(all_orders):
            next_order = self.market_cache.incr('manual_order_count')
            #self.manual_positions['MN'+str(next_order)] = all_orders
            self.position_book['MN' + str(next_order)] = all_orders
            self.market_cache.set('manual_positions', self.position_book)



    def close_manual_position(self, id, orders):
        print('close_manual_position', orders)
        if self.trade_date is None: #Hack
            self.trade_date = time.strftime('%Y-%m-%d')
        all_orders_success = True
        all_orders = []
        for order in orders:
            optimal_order = self.get_manual_entry_order_info(order)
            for broker in self.brokers:
                res = broker.place_entry_order(optimal_order, 'MARKET')
                all_orders_success = all_orders_success and res['success']
                all_orders.append(res)

        if all_orders_success and len(all_orders):

            del self.position_book[id]
            #del self.manual_positions[id]
            self.market_cache.set('manual_positions', self.position_book)


    def clear_manual_position(self, id):
        print('clear_manual_position')
        del self.position_book[id]
        self.market_cache.set('manual_positions', self.position_book)
