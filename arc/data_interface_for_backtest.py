from servers.server_settings import cache_dir
from diskcache import Cache
from arc.oms_manager import OMSManager


class AlgorithmBacktestIterface:
    def __init__(self):
        self.market_cache = Cache(cache_dir + 'oms_cache')
        self.oms_manager = OMSManager(place_live_orders=True, market_cache=self.market_cache)

    def notify_pattern_signal(self, ticker, pattern, pattern_match_idx=None):
        pass

    def place_entry_order(self, symbol, order_side, qty, strategy_id, order_id, order_type, option_flag,cover ):
        print('place_entry_order in data interface', symbol, order_side, qty, strategy_id, order_id,order_type, option_flag, cover)
        order_info = {'symbol': symbol,
                      'order_side':order_side,
                      'qty': qty,
                      'strategy_id': strategy_id,
                      'order_id': order_id,
                      'order_type': order_type,
                      'option_flag':option_flag,
                      'cover':cover
                      }
        resp = self.oms_manager.place_entry_order(order_info)
        print(resp)

    def place_exit_order(self, symbol, order_side, qty, strategy_id, order_id, order_type, option_flag ):
        print('place_exit_order in data interface', symbol, order_side, qty, strategy_id, order_id,order_type)
        order_info = {'symbol': symbol,
                      'order_side':order_side,
                      'qty': qty,
                      'strategy_id': strategy_id,
                      'order_id': order_id,
                      'order_type': order_type,
                      'option_flag': option_flag
                      }
        resp = self.oms_manager.place_exit_order(order_info)
        print(resp)
