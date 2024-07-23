from infrastructure.fyers.historical_data import FyersFeed
#from portfolio.serializers import TradeSerializer, TradeDetailsSerializer
import requests
from config import order_api
import json
from datetime import datetime as dt
from helper.utils import get_broker_order_type
from config import is_month_end_expiry
order_type_dict = {'LONG' : 1, 'SHORT' : -1, 'BUY' : 1, 'SELL' : -1}
success_code = 1101

class BrokerLive:
    def __init__(self,pm):
        self.id = 'BASANT_FYERS'
        self.fyers_feed = FyersFeed.getInstance()
        self.pm = pm
        self.get_funds()

    def refresh(self):
        self.fyers_feed.authenicate()

    def get_funds(self):
        funds_resp = self.fyers_feed.fyers.funds()
        #print('get_funds', funds_resp)
        print('get_funds=====', funds_resp['fund_limit'])
        total_funds = 0
        for bal in funds_resp['fund_limit']:
            if bal['title'] in ['Limit at start of the day', 'Realized Profit and Loss']:
                total_funds += bal['equityAmount']
        """
        order_book = self.fyers_feed.fyers.orderbook()
        print('order_book')
        print(order_book)
        """
        """
        orderId = "2220802169801"
        data = {"id": orderId}
        order_details = self.get_order_status(orderId)
        print('order_details')
        print(order_details)
        """
        """
        positions = self.fyers_feed.fyers.positions()
        print('positions')
        print(positions)
        """
        """
        tradebook = self.fyers_feed.fyers.tradebook()
        print('tradebook')
        print(tradebook)
        """
        #print(total_funds)

    def get_order_book(self):
        _resp = self.fyers_feed.fyers.orderbook()

    def get_order_status(self,orderId):
        data = {"id": orderId}
        try:
            _resp = self.fyers_feed.fyers.orderbook(data=data)['orderBook'][0]
        except:
            _resp = {}
        return _resp

    def get_current_positions(self):
        _resp = self.fyers_feed.fyers.positions()
        return _resp

    def get_tradebook(self):
        _resp = self.fyers_feed.fyers.tradebook()

    def place_multi_order(self):
        "pass array upto 10 to order place api"
        pass
    def modify_order(self):
        orderId = "8102710298291"
        data = {
            "id": orderId,
            "type": 1,
            "limitPrice": 61049,
            "qty": 1
        }

        self.fyers_feed.fyers.modify_order(data)
    def cancel_order(self):
        data = {"id": '808058117761'}
        self.fyers_feed.fyers.cancel_order(data)

    def exit_position(self, order_id):
        data = {"id":order_id}
        print ('exit position', data)
        resp = self.fyers_feed.fyers.exit_positions(data)
        print(resp)

    def exit_all_positions(self):
        self.fyers_feed.fyers.exit_positions()

    def get_market_status(self):
        self.fyers_feed.fyers.market_status()

    def place_intraday_limit_order(self,symbol,qty, side):
        underlying = symbol.split(':')[1].split('-')[0]
        order_details = self.pm.get_optimal_order_info(underlying, side)
        print(order_details)
        exp = dt.strptime(order_details['expiry'], '%y%m%d').strftime('%y%-m%d')
        sym = "NSE:" + order_details['underlying'] + exp + str(order_details['strike']) + order_details['type']
        data = {
              "symbol":sym,  #symbol, #NSE:BANKNIFTY22MAR36500CE
              "qty":order_details['quantity'],
              "type":1,
              "side":order_type_dict['BUY'],
              "productType":"MARGIN",
              "limitPrice": order_details['price'],
               "stopPrice":0,
              "disclosedQty":0,
            "validity": "DAY",
            "offlineOrder": "False",
            }
        print(data)

        #response = self.fyers_feed.fyers.place_order(data)
        #print(response)
        # https://myapi.fyers.in/docs/#tag/Order-Placement/paths/~1OthePlacement/get
        return order_details

    def place_basket_order(self, order_list):
        response = self.fyers_feed.fyers.place_basket_orders(order_list)
        # TODO : implementation pending
        return 'res'


    def place_intraday_market_order(self,order_info):
        print(order_info)
        response = self.fyers_feed.fyers.place_order(order_info)
        print(response)
        res = {'success': response['code'] == success_code, 'order_id': response['id'], "position_id": order_info["symbol"] + "-" + order_info["productType"], 'qty': order_info["qty"], 'side': order_info['side']}
        res = {'success': response['code'] == success_code, 'order_id': response['id'], "symbol": order_info["symbol"], 'qty': order_info["qty"], 'side': order_info['side']}
        res['traded_price'] = self.get_order_status(response['id']).get('tradedPrice', -9999)
        return res

    def convert_to_valid_entry_order(self, order_details):
        #print(order_details)
        category = order_details['order_type']
        print(order_details)
        data = {
            "symbol": order_details['symbol'], #'NSE:BANKNIFTY2260936000CE',
            "qty": order_details['qty'],
            "type": 1 if category == 'LIMIT' else 2 if category == 'MARKET' else 0,
            "side": get_broker_order_type(order_details['order_side']),
            "productType": "MARGIN",
            "limitPrice": order_details['price'] if category == 'LIMIT' else 0 if category == 'MARKET' else 0,
            "stopPrice": 0,
            "disclosedQty": 0,
            "validity": "DAY",
            "offlineOrder": "False",
            "stopLoss": 0,
            "takeProfit": 0
        }

        # response = self.fyers_feed.fyers.place_order(data)
        # print(response)
        # https://myapi.fyers.in/docs/#tag/Order-Placement/paths/~1OthePlacement/get
        return data

    def convert_to_valid_exit_order(self, order_details, category):
        data = {
            "symbol": order_details['symbol'], #'NSE:BANKNIFTY2260936000CE',
            "qty": order_details['qty'],
            "type": 1 if category == 'LIMIT' else 2 if category == 'MARKET' else 0,
            "side": get_broker_order_type(order_details['side']),
            "productType": "MARGIN",
            "limitPrice": order_details['price'] if category == 'LIMIT' else 0 if category == 'MARKET' else 0,
            "stopPrice": 0,
            "disclosedQty": 0,
            "validity": "DAY",
            "offlineOrder": "False",
            "stopLoss": 0,
            "takeProfit": 0
        }

        # response = self.fyers_feed.fyers.place_order(data)
        # print(response)
        # https://myapi.fyers.in/docs/#tag/Order-Placement/paths/~1OthePlacement/get
        return data

    def place_entry_order(self, order_info):
        print('broker place_entry order')
        if order_info['order_type'] == 'MARKET':
            order_details = self.convert_to_valid_entry_order(order_info)
            res = self.place_intraday_market_order(order_details)
            return res
            #return {'success': True}

    def place_exit_order(self, order_info, category):
        print('broker place_ exit order')
        if category == 'MARKET':
            order_details = self.convert_to_valid_exit_order(order_info,category)
            print(order_details)
            res = self.place_intraday_market_order(order_details)
            print(res)
            return res
            #return {'success': True}


