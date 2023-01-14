import requests
from config import order_api
import json
class DummyBroker:
    def create_intraday_market_order(self, strat_id, signal_id,trigger_seq, symbol, side, price, qty, date, time ):
        data = {
            "order_date":date,
            "order_time": time,
            "strat_id": strat_id,
            "signal_id": signal_id,
            "trigger_id": trigger_seq,
            "order_type": "MARKET",
            "symbol":symbol,
            "side":side,
            "quantity": qty,
            "price": price,
            "product":"INTRADAY"
            }
        return data

    def place_order(self, strat_id, signal_id,trigger_seq, symbol, side, price, qty, date, time):
        order_data = self.create_intraday_market_order(strat_id, signal_id,trigger_seq, symbol, side, price, qty, date, time)
        headers = {
            'Content-type': 'application/json',
            'Accept': 'application/json'
        }
        print('place dummy order')

        x = requests.post(order_api, headers=headers, data=json.dumps(order_data))
        print(x.text)


